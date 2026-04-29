#!/usr/bin/env python3
"""Unit tests for CORECONFDatastore._create_xpath()."""

import unittest
import helpers

import pycoreconf
from pycoreconf.datastore import CORECONFDatastore


class _SimpleModel:
    """Minimal stub: one container, one leaf, no list."""
    def __init__(self):
        self.sids = {
            "/root": 100,
            "/root/leaf": 101,
        }
        self.ids = {v: k for k, v in self.sids.items()}
        self.key_mapping = {}
        self.types = {"/root/leaf": "string"}


class _StringKeyModel:
    """Stub with one list keyed by a single string leaf."""
    def __init__(self):
        self.sids = {
            "/root": 100,
            "/root/list": 110,
            "/root/list/name": 111,
            "/root/list/value": 112,
        }
        self.ids = {v: k for k, v in self.sids.items()}
        self.key_mapping = {"110": [111]}
        self.types = {
            "/root/list/name": "string",
            "/root/list/value": "string",
        }


class _EnumKeyModel:
    """Stub with one list keyed by an enum leaf and a uint leaf."""
    def __init__(self):
        self.sids = {
            "/root": 100,
            "/root/list": 110,
            "/root/list/mode": 111,
            "/root/list/id": 112,
        }
        self.ids = {v: k for k, v in self.sids.items()}
        self.key_mapping = {"110": [111, 112]}
        self.types = {
            "/root/list/mode": {"0": "direct", "1": "delta"},
            "/root/list/id": "uint8",
        }


class _IdentityrefKeyModel:
    """Stub with one list keyed by an identityref leaf and a uint leaf."""
    def __init__(self):
        self.sids = {
            "/root": 100,
            "/root/list": 110,
            "/root/list/type": 111,
            "/root/list/id": 112,
        }
        self.ids = {v: k for k, v in self.sids.items()}
        # SID 200 is an identity node: its YANG path is "/mymod:solar-radiation"
        self.ids[200] = "/mymod:solar-radiation"
        self.key_mapping = {"110": [111, 112]}
        self.types = {
            "/root/list/type": "identityref",
            "/root/list/id": "uint8",
        }


class TestCreateXpathUnknownSid(unittest.TestCase):
    def test_raises_key_error(self):
        ds = CORECONFDatastore(_SimpleModel(), {})
        with self.assertRaises(KeyError):
            ds._create_xpath(9999)


class TestCreateXpathNoList(unittest.TestCase):
    def setUp(self):
        self.ds = CORECONFDatastore(_SimpleModel(), {})

    def test_container(self):
        self.assertEqual(self.ds._create_xpath(100), "/root")

    def test_leaf(self):
        self.assertEqual(self.ds._create_xpath(101), "/root/leaf")

    def test_extra_keys_ignored_when_no_list(self):
        self.assertEqual(self.ds._create_xpath(101, keys=["ignored"]), "/root/leaf")


class TestCreateXpathStringKey(unittest.TestCase):
    def setUp(self):
        self.ds = CORECONFDatastore(_StringKeyModel(), {})

    def test_list_node_with_key(self):
        self.assertEqual(self.ds._create_xpath(110, keys=["foo"]), "/root/list[name='foo']")

    def test_leaf_inside_list(self):
        self.assertEqual(self.ds._create_xpath(112, keys=["foo"]), "/root/list[name='foo']/value")

    def test_list_node_without_keys(self):
        self.assertEqual(self.ds._create_xpath(110), "/root/list")


class TestCreateXpathEnumKey(unittest.TestCase):
    def setUp(self):
        self.ds = CORECONFDatastore(_EnumKeyModel(), {})

    def test_int_enum_key_resolved_to_name(self):
        # int key 1 → enum value "delta"
        result = self.ds._create_xpath(110, keys=[1, 7])
        self.assertEqual(result, "/root/list[mode='delta'][id='7']")

    def test_string_enum_key_passed_through(self):
        result = self.ds._create_xpath(110, keys=["direct", "3"])
        self.assertEqual(result, "/root/list[mode='direct'][id='3']")

    def test_unknown_int_enum_kept_as_is(self):
        # int 99 not in enum map → rendered as "99"
        result = self.ds._create_xpath(110, keys=[99, 0])
        self.assertEqual(result, "/root/list[mode='99'][id='0']")


class TestCreateXpathIdentityrefKey(unittest.TestCase):
    def setUp(self):
        self.ds = CORECONFDatastore(_IdentityrefKeyModel(), {})

    def test_int_identityref_key_resolved_to_path(self):
        # int SID 200 → ids[200] = "/mymod:solar-radiation"
        result = self.ds._create_xpath(110, keys=[200, 0])
        self.assertEqual(result, "/root/list[type='/mymod:solar-radiation'][id='0']")

    def test_string_identityref_key_passed_through(self):
        result = self.ds._create_xpath(110, keys=["solar-radiation", "0"])
        self.assertEqual(result, "/root/list[type='solar-radiation'][id='0']")


class TestCreateXpathRoundTrip(unittest.TestCase):
    """Integration tests using the real coreconf-m2m model."""

    @classmethod
    def setUpClass(cls):
        sid_path = helpers.resolve_filepath("samples/datastore/coreconf-m2m@2026-03-29.sid")
        cls.model = pycoreconf.CORECONFModel(sid_path)
        cls.ds = cls.model.create_datastore()

    def _assert_roundtrip(self, xpath):
        sid, keys = self.ds._resolve_xpath(xpath)
        rebuilt = self.ds._create_xpath(sid, keys=keys)
        sid2, keys2 = self.ds._resolve_xpath(rebuilt)
        self.assertEqual(sid, sid2, f"SID mismatch for xpath: {xpath!r}")
        self.assertEqual(keys, keys2, f"Keys mismatch for xpath: {xpath!r}")

    def test_list_node_roundtrip(self):
        self._assert_roundtrip(
            "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']"
        )

    def test_leaf_inside_list_roundtrip(self):
        self._assert_roundtrip(
            "/transducers/transducer[type='coreconf-m2m:wind-speed'][id='1']/quantity/value"
        )

    def test_different_entry_roundtrip(self):
        self._assert_roundtrip(
            "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/quantity/statistics/sample-count"
        )


if __name__ == "__main__":
    unittest.main()
