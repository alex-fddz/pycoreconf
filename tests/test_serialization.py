import unittest
import helpers
import pycoreconf
from pycoreconf.model import ConfigValidationError
import json

try:
    import yangson
except ImportError:
    yangson = None


class TestSerialization(unittest.TestCase):
    # Helper: create model from one or more SID paths (relative from project root)
    def make_ccm(self, sid_paths, desc_file=None):
        if isinstance(sid_paths, str):
            sid_paths = [sid_paths]
        sid_paths = [helpers.resolve_filepath(p) for p in sid_paths]
        return pycoreconf.CORECONFModel(
            sid_files=sid_paths,
            model_description_file=helpers.resolve_filepath(desc_file)
        )

    # Helper: load a config.json file into a JSON string
    def load_config_file(self, json_filepath):
        with open(helpers.resolve_filepath(json_filepath), 'r') as f:
            config_obj = json.load(f)
        return json.dumps(config_obj)

    def test_encode_decode_roundtrip_json_string(self):
        """Test encode/decode with JSON string input - roundtrip to same data."""
        ccm = self.make_ccm("samples/basic/example-1.sid")
        config = '{"example-1:greeting": {"message": "Hello"}}'
        config_parsed = json.loads(config)

        cbor_data = ccm.encode_json(config)
        decoded = ccm.decode(cbor_data)

        self.assertIsInstance(cbor_data, bytes)
        self.assertIsInstance(decoded, dict)
        self.assertEqual(config_parsed, decoded)


    def test_encode_decode_roundtrip_dict(self):
        """Test encode/decode with dict input - roundtrip to same data."""
        ccm = self.make_ccm("samples/basic/example-1.sid")
        config = {"example-1:greeting": {"message": "Hello"}}

        cbor_data = ccm.encode(config)
        decoded = ccm.decode(cbor_data)

        self.assertIsInstance(cbor_data, bytes)
        self.assertIsInstance(decoded, dict)
        self.assertEqual(config, decoded)

    def test_encode_json_file_roundtrip(self):
        """Test encode_json with file path - roundtrip back to same data."""
        ccm = self.make_ccm("samples/basic/example-1.sid")
        config_file = helpers.resolve_filepath("samples/basic/ex1-config.json")

        with open(config_file, 'r') as f:
            original_config = json.load(f)

        cbor_data = ccm.encode_json(config_file)
        decoded = ccm.decode(cbor_data)

        self.assertIsInstance(cbor_data, bytes)
        self.assertIsInstance(decoded, dict)
        self.assertEqual(original_config, decoded)

    def test_decode_to_json(self):
        """Test decode_to_json returns JSON string matching original."""
        ccm = self.make_ccm("samples/basic/example-1.sid")
        config = '{"example-1:greeting": {"message": "Hello"}}'

        cbor_data = ccm.encode_json(config)
        json_str = ccm.decode_to_json(cbor_data)

        parsed = json.loads(json_str)
        original = json.loads(config)

        self.assertIsInstance(cbor_data, bytes)
        self.assertIsInstance(json_str, str)

        self.assertEqual(original, parsed)
        self.assertEqual(config, json_str)
    
    def test_encode_json_invalid_json_raises(self):
        """Test encode_json with invalid JSON string."""
        ccm = self.make_ccm("samples/basic/example-1.sid")
        with self.assertRaises(json.decoder.JSONDecodeError):
            ccm.encode_json("{invalid")
        with self.assertRaises(FileNotFoundError):
            ccm.encode_json("not-here.json")

    def test_multifile_serialization_roundtrip(self):
        """Test encode/decode with multiple SID files - roundtrip to same data."""
        sids = [
            "samples/multisid/ietf-schc@2023-01-28.sid",
            "samples/multisid/ietf-schc-oam@2021-11-10.sid"
        ]
        ccm = self.make_ccm(sids)
        config_str = self.load_config_file("samples/multisid/schc.json")
        config = json.loads(config_str)

        cbor_data = ccm.encode_json(config_str)
        decoded = ccm.decode(cbor_data)

        self.assertEqual(config, decoded)

    def test_identityref_encoding(self):
        """Test identityref encoding roundtrip."""
        sids = [
            "samples/multisid/ietf-schc@2023-01-28.sid",
            "samples/multisid/ietf-schc-oam@2021-11-10.sid"
        ]
        ccm = self.make_ccm(sids)
        config = {
            "ietf-schc:schc": { "rule": [ {
                "rule-nature":"ietf-schc:nature-compression",
                "entry": [ {
                    "field-length":"ietf-schc:fl-token-length",
                } ]
            } ] } }
        expected = bytes.fromhex("a119eabfa10181a2182319eab80481a107d82d19eaac")

        encoded = ccm.encode(config)
        self.assertEqual(encoded, expected)

        decoded = ccm.decode(encoded)
        self.assertEqual(config, decoded)

class TestValidation(unittest.TestCase):
    def make_ccm(self, sid_paths, desc_file=None):
        if isinstance(sid_paths, str):
            sid_paths = [sid_paths]
        sid_paths = [helpers.resolve_filepath(p) for p in sid_paths]
        return pycoreconf.CORECONFModel(
            sid_files=sid_paths,
            model_description_file=helpers.resolve_filepath(desc_file)
        )

    @unittest.skipIf(yangson is None, "yangson not installed")
    def test_validate_json_valid_config(self):
        """Test validate_json with valid config does not raise."""
        ccm = self.make_ccm("samples/validation/example-4-a.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        config = '{"example-4-a:bag": {"foo": 42}}'

        ccm.validate_json(config)

        # Workflow test: ensure validated input doesn't break
        expected = bytes.fromhex("a119ea61a102182a")
        self.assertEqual(ccm.encode_json(config), expected)


    @unittest.skipIf(yangson is None, "yangson not installed")
    def test_validate_json_invalid_config_raises(self):
        """Test validate_json with invalid config raises."""
        ccm = self.make_ccm("samples/validation/example-4-a.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        config = '{"example-4-a:bag": {"foo": 256}}'

        with self.assertRaises(ConfigValidationError) as e:
            ccm.validate_json(config)
        err = str(e.exception)
        self.assertIn("invalid-type: expected uint8", err)
        self.assertIn("{/example-4-a:bag/foo}", err)

    def test_no_encode_decode_validation(self):
        """Lock-in behavior of no validation during encoding and decoding."""
        ccm = self.make_ccm("samples/validation/example-4-a.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        config = '{"example-4-a:bag": {"foo": 256}}' # invalid: foo is uint8
        expected_cbor = bytes.fromhex("a119ea61a102190100")

        # These must not validate
        cbor_from_json = ccm.encode_json(config)
        decoded_json = ccm.decode_to_json(cbor_from_json)

        cbor_from_dict = ccm.encode(json.loads(config))
        decoded_dict = ccm.decode(cbor_from_json)

        self.assertIsInstance(decoded_dict, dict)
        self.assertIsInstance(decoded_json, str)

        self.assertEqual(decoded_json, config)
        self.assertEqual(decoded_dict, json.loads(config))

        self.assertEqual(cbor_from_json, expected_cbor)
        self.assertEqual(cbor_from_json, cbor_from_dict)


if __name__ == "__main__":
    unittest.main()
