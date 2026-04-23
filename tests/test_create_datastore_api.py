#!/usr/bin/env python3
"""Unit tests for new create_datastore* API methods."""

import unittest
import json
import helpers

import pycoreconf


class TestCreateDatastoreAPI(unittest.TestCase):
    """Tests for the new create_datastore* factory methods."""

    @classmethod
    def setUpClass(cls):
        cls.sid_path = helpers.resolve_filepath("samples/datastore/coreconf-m2m@2026-03-29.sid")
        cls.model = pycoreconf.CORECONFModel(cls.sid_path)

    def test_create_datastore_from_cbor_empty(self):
        """Test create_datastore_from_cbor with empty CBOR."""
        cbor_data = bytes.fromhex("a0")
        ds = self.model.create_datastore_from_cbor(cbor_data)

        result = json.loads(ds.to_json())
        self.assertEqual(result, {})

    def test_create_datastore_from_cbor_with_data(self):
        """Test create_datastore_from_cbor with data from encode()."""
        json_input = '{"coreconf-m2m:transducers": {"transducer": []}}'
        cbor_data = self.model.encode_json(json_input)
        ds = self.model.create_datastore_from_cbor(cbor_data)

        result = json.loads(ds.to_json())
        self.assertIn("coreconf-m2m:transducers", result)

    def test_create_datastore_from_json_string(self):
        """Test create_datastore_from_json with JSON string."""
        json_str = '{"coreconf-m2m:transducers": {"transducer": []}}'
        ds = self.model.create_datastore_from_json(json_str)

        result = json.loads(ds.to_json())
        self.assertIn("coreconf-m2m:transducers", result)

    def test_create_datastore_with_identifier_dict(self):
        """Test create_datastore with identifier-keyed dict."""
        config = {"coreconf-m2m:transducers": {"transducer": []}}
        ds = self.model.create_datastore(config)

        result = json.loads(ds.to_json())
        self.assertIn("coreconf-m2m:transducers", result)

    def test_create_datastore_empty(self):
        """Test create_datastore with no arguments creates empty datastore."""
        ds = self.model.create_datastore()

        result = json.loads(ds.to_json())
        self.assertEqual(result, {})

    def test_roundtrip_json_to_datastore_and_back(self):
        """Test full roundtrip: JSON -> datastore -> JSON."""
        original = '{"coreconf-m2m:transducers": {"transducer": []}}'
        ds = self.model.create_datastore_from_json(original)

        result = ds.to_json()
        self.assertIn("coreconf-m2m:transducers", result)

    def test_roundtrip_dict_to_datastore_and_back(self):
        """Test full roundtrip: dict -> datastore -> JSON."""
        config = {"coreconf-m2m:transducers": {"transducer": []}}
        ds = self.model.create_datastore(config)

        result = ds.to_json()
        self.assertIn("coreconf-m2m:transducers", result)


if __name__ == "__main__":
    unittest.main()
