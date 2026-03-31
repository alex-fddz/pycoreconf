#!/usr/bin/env python3
"""Unit tests for CORECONFDatastore.predicates()."""

import unittest
import helpers

import pycoreconf


class _DummyEnumKeyModel:
    """Minimal model stub for enum-key path resolution tests."""

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

    def findSID(self, *_args, **_kwargs):
        raise AssertionError("findSID should not be called for predicates() with predicates")


class TestGetKeys(unittest.TestCase):
    def test_enum_key_is_converted_both_directions(self):
        ds = pycoreconf.CORECONFDatastore(_DummyEnumKeyModel(), {})

        sid, keys = ds._resolve_path("/root/list[mode='delta'][id='7']")
        self.assertEqual(sid, 110)
        self.assertEqual(keys, [1, 7])

        self.assertEqual(
            ds.predicates("/root/list[mode='delta'][id='7']"),
            ["[mode='delta'][id='7']"],
        )

    def test_predicates_on_measurement_list(self):
        sid_path = helpers.resolve_filepath("samples/terraforma/atmos-41-weather-station@2026-03-02.sid")

        model = pycoreconf.CORECONFModel(sid_path)
        ds = model.create_datastore()

        ds["/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']"] = {}
        ds["/measurements/measurement[type='atmos-41-weather-station:wind-speed'][id='1']"] = {}

        keys = ds.predicates("/measurements/measurement")

        self.assertIsInstance(keys, list)

        expected = [
            "[type='solar-radiation'][id='0']",
            "[type='wind-speed'][id='1']",
        ]
        self.assertCountEqual(keys, expected)

    def test_predicates_with_predicates(self):
        sid_path = helpers.resolve_filepath("samples/terraforma/atmos-41-weather-station@2026-03-02.sid")

        model = pycoreconf.CORECONFModel(sid_path)
        ds = model.create_datastore()

        keys = ds.predicates(
            "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='2']"
        )

        self.assertEqual(
            keys,
            ["[type='solar-radiation'][id='2']"],
        )

    def test_compact_identity_filter_is_reusable(self):
        sid_path = helpers.resolve_filepath("samples/terraforma/atmos-41-weather-station@2026-03-02.sid")

        model = pycoreconf.CORECONFModel(sid_path)
        ds = model.create_datastore()

        ds["/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/sample-count"] = 123

        filters = ds.predicates("/measurements/measurement")
        self.assertIn("[type='solar-radiation'][id='0']", filters)

        path = "/measurements/measurement[type='solar-radiation'][id='0']/sample-count"
        self.assertEqual(ds[path], 123)



if __name__ == "__main__":
    unittest.main()
