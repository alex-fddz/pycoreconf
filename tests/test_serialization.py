import unittest
import helpers
import pycoreconf
import json
from yangson.exceptions import YangTypeError

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
        ccm = self.make_ccm("samples/basic/example-1@unknown.sid")
        config = self.load_config_file("samples/basic/ex1-config.json")
        decoded = self.roundtrip(ccm, config)
        self.assertEqual(config, decoded)

    # 2. basic serialization roundtrip with config validation
    def test_serialization_with_validation_valid_config(self):
        ccm = self.make_ccm("samples/validation/example-4-a@unknown.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        config = { "example-4-a:bag": { "foo": 42 } }

        valid = ccm.validateConfig(config)
        self.assertEqual(valid, True)

        # config = json.dumps(config)
        # Test encode/decode roundtrip
        decoded = self.roundtrip(ccm, config)
        self.assertEqual(config, decoded)

    def test_serialization_with_validation_invalid_input_config_raises(self):
        ccm = self.make_ccm("samples/validation/example-4-a@unknown.sid",
                            desc_file="samples/validation/description.json")
        ccm.add_modules_path([
            helpers.resolve_filepath("samples/validation/"),
            helpers.resolve_filepath("samples/validation/ietf/")
        ])

        # model says foo is uint8
        bad_cfg = { "example-4-a:bag": { "foo": 256 } }

        with self.assertRaises(YangTypeError) as cm:
            # call the code that should raise, e.g. apply/validate the config
            ccm.validateConfig(bad_cfg)

        # Optionally assert the exception message contains the expected substring
        err = str(cm.exception)
        self.assertIn("invalid-type: expected uint8", err)
        self.assertIn("{/example-4-a:bag/foo}", err)

        with self.assertRaises(pycoreconf.ConfigValidationError) as cm:
            ccm.toCORECONF(json.dumps(bad_cfg))

    def test_serialization_with_validation_invalid_output_config_raises(self):
        ccm = self.make_ccm("samples/validation/example-4-a@unknown.sid",
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

        with self.assertRaises(pycoreconf.ConfigValidationError) as cm:
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

if __name__ == "__main__":
    unittest.main()

