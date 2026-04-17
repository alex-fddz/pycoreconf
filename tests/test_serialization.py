import unittest
import helpers
import pycoreconf
from pycoreconf.model import ConfigValidationError
import json

try:
    from yangson.exceptions import YangTypeError
except ImportError:
    YangTypeError = None

class TestPyCoreConf(unittest.TestCase):
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

    # Helper: roundtrip encode/decode
    def roundtrip(self, ccm, config):
        encoded = ccm.toCORECONF(config)
        decoded = ccm.toJSON(encoded, return_pydict=isinstance(config, dict))
        return decoded

    # 1. simple basic serialization roundtrip
    def test_basic_serialization_roundtrip(self):
        ccm = self.make_ccm("samples/basic/example-1.sid")
        config = self.load_config_file("samples/basic/ex1-config.json")
        decoded = self.roundtrip(ccm, config)
        self.assertEqual(config, decoded)

    # 2. basic serialization roundtrip with config validation
    @unittest.skipIf(YangTypeError is None, "yangson not installed")
    def test_serialization_with_validation_valid_config(self):
        ccm = self.make_ccm("samples/validation/example-4-a.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        config = { "example-4-a:bag": { "foo": 42 } }

        # Should not raise
        ccm._validate_config(config)

        # config = json.dumps(config)
        # Test encode/decode roundtrip
        decoded = self.roundtrip(ccm, config)
        self.assertEqual(config, decoded)

    @unittest.skipIf(YangTypeError is None, "yangson not installed")
    def test_serialization_with_validation_invalid_input_config_raises(self):
        ccm = self.make_ccm("samples/validation/example-4-a.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        # model says foo is uint8
        bad_cfg = { "example-4-a:bag": { "foo": 256 } }

        with self.assertRaises(YangTypeError) as cm:
            # call the code that should raise, e.g. apply/validate the config
            ccm._validate_config(bad_cfg)

        # Optionally assert the exception message contains the expected substring
        err = str(cm.exception)
        self.assertIn("invalid-type: expected uint8", err)
        self.assertIn("{/example-4-a:bag/foo}", err)

        with self.assertRaises(ConfigValidationError) as cm:
            ccm.toCORECONF(json.dumps(bad_cfg))

    @unittest.skipIf(YangTypeError is None, "yangson not installed")
    def test_serialization_with_validation_invalid_output_config_raises(self):
        ccm = self.make_ccm("samples/validation/example-4-a.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        # model says foo is uint8
        bad_cbor_data = bytes([
            0xA1,             # map(1)
            0x19, 0xEA, 0x61, # unsigned(60001)
            0xA1,             # map(1)
            0x02,             # unsigned(2)
            0x19, 0x01, 0x00, # unsigned(256)
        ])

        with self.assertRaises(ConfigValidationError) as cm:
            ccm.toJSON(bad_cbor_data)

    # 3. multisid serialization roundtrip
    def test_multifile_serialization_roundtrip(self):
        sids = [
            "samples/multisid/ietf-schc@2023-01-28.sid",
            "samples/multisid/ietf-schc-oam@2021-11-10.sid"
        ]
        ccm = self.make_ccm(sids)
        config = self.load_config_file("samples/multisid/schc.json")
        decoded = self.roundtrip(ccm, config)
        self.assertEqual(config, decoded)

    # 4. identityref encoding: standalone and within union
    def test_identityref_encoding(self):
        sids = [
            "samples/multisid/ietf-schc@2023-01-28.sid",
            "samples/multisid/ietf-schc-oam@2021-11-10.sid"
        ]
        ccm = self.make_ccm(sids)
        config = {
            "ietf-schc:schc": { "rule": [ {
                "rule-nature":"ietf-schc:nature-compression", # idref encoded as unsigned(60088)
                "entry": [ {
                    "field-length":"ietf-schc:fl-token-length", # union[idref] encoded as 45(60076)
                    } ]
            } ] } }
        expected = bytes.fromhex("a119eabfa10181a2182319eab80481a107d82d19eaac")
        encoded = ccm.toCORECONF(config)
        self.assertEqual(encoded, expected)
        decoded = ccm.toJSON(encoded, return_pydict=True)
        self.assertEqual(config, decoded)

if __name__ == "__main__":
    unittest.main()

