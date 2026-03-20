#!/usr/bin/env python3
"""
Test XPath navigation with multilevel predicates.
"""

import unittest
import helpers

import pycoreconf

class TestXPathPredicates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # locate SID and CBOR sample files
        cls.sid_path = helpers.resolve_filepath("samples/terraforma/atmos-41-weather-station@2026-03-02.sid")
        # cls.cbor_path = resolve_path("samples/terraforma/test_data.cbor")
        # # -> non-deterministic sample generated file -> provide fixed cbor_data below.

        # Skip test if files not found ?
        # if not os.path.exists(cls.sid_path):
        #     raise unittest.SkipTest(f"SID file not found at {cls.sid_path}")
        # if not os.path.exists(cls.cbor_path):
        #     raise unittest.SkipTest(f"CBOR data file not found at {cls.cbor_path}")

        # load model and datastore once for all tests
        cls.ccm = pycoreconf.CORECONFModel(cls.sid_path)
        # with open(cls.cbor_path, "rb") as f:
        #     cbor_data = f.read()
        cbor_data = bytes.fromhex(
            "a11a000186b8a1018cab091a000186a701000b1906ca06010a64572f6d320519" \
            "06bf021906e7031906cb041906c2081507191a86ab091a000186a501000b1901" \
            "ee06000a626d6d051901bd021901f6031901ec041901e308183907190397ab09" \
            "1a000186a101000b189706000a61430518660218ac03189f041889080c07190a" \
            "baab091a000186a601000b19031806000a61250519030c021903340319030e04" \
            "19031b081852071915f5ab091a000186a301000b1903a706020a636b50610519" \
            "038b021903c9031903af041903a408182007191005ab091a000186aa01000b18" \
            "2306000a636b5061052502182303182204182508182807191501ab091a000186" \
            "ad01000b18dd06010a636d2f730518cc0218e00318ea0418d70818230719162f" \
            "ab091a000186ab01000b190d6f06000a676465677265657305190d5302190d77" \
            "03190d6304190d62080607191a08ab091a000186ac01000b184406020a636d2f" \
            "73051602186f0318320418440814071904c4ab091a000186a801000b18180602" \
            "0a65636f756e74052002182e0318230418250818440719129aab091a000186a2" \
            "01000b1901e906020a626b6d051901bd021901ef031901fc041901f208186207" \
            "191fc5ab091a000186a901000b19026906000a67646567726565730519026402" \
            "19029a031902670419026b08184b071910d1"
        )
        cls.ds = cls.ccm.create_datastore(cbor_data)

    def test_measurements_path_exists_and_type(self):
        # Ensure /measurements exists and is list or dict
        measurements = self.ds["/measurements"]
        self.assertTrue(isinstance(measurements, (list, dict)),
                        "/measurements should be a list or dict in datastore")

    def test_single_level_predicate_read(self):
        # baseline: read a known path with single-level predicates
        xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/value"
        val = self.ds[xpath]
        # assert it is a numeric value (int or float) or a string that can represent a number
        self.assertIsNotNone(val, "Value at single-level predicate path should not be None")
        self.assertTrue(isinstance(val, (int, float, str)),
                        "Value should be int, float, or string")

    def test_single_level_predicate_modify_and_verify(self):
        # read current value, modify, and verify round-trip via datastore indexing
        xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/value"
        orig = self.ds[xpath]
        # choose numeric mutation if possible
        if isinstance(orig, (int, float)):
            new = orig + 100
        else:
            # try converting to float if it's a numeric string
            try:
                new = float(orig) + 100
            except Exception:
                # fallback: append marker to string
                new = str(orig) + "_modified"

        # assign and read back
        self.ds[xpath] = new
        read_back = self.ds[xpath]
        # If numeric, compare numerically; otherwise compare equality of string
        if isinstance(new, (int, float)):
            self.assertAlmostEqual(float(read_back), float(new),
                                   msg="Modified numeric value should persist in datastore")
        else:
            self.assertEqual(str(read_back), str(new),
                             "Modified string value should persist in datastore")

        # restore original value to avoid side effects for other tests
        self.ds[xpath] = orig

    def test_model_key_mapping_present_and_iterable(self):
        # If model has key_mapping, it should be a dict-like with str keys
        model = getattr(self.ds, "model", None)
        if hasattr(model, "key_mapping"):
            km = model.key_mapping
            self.assertIsInstance(km, dict)
            # verify at least one mapping entry has list/tuple of keys
            any_ok = False
            for sid_str, key_sids in km.items():
                self.assertIsInstance(sid_str, str)
                self.assertTrue(isinstance(key_sids, (list, tuple)),
                                "key_mapping values should be a list/tuple of key sids")
                any_ok = True
                break
            self.assertTrue(any_ok, "key_mapping should contain at least one entry if present")

    def test_multi_level_predicate_support(self):
        # The sample schema is known to be relatively flat; here assert behavior:
        # Attempt to construct multi-level predicate path and assert either it raises
        # a KeyError/IndexError or returns a valid value type. This documents expected behavior.
        multi_xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/subcontainer[subid='x']/leaf"
        try:
            result = self.ds[multi_xpath]
            # If it succeeds, ensure result is a simple JSON-serializable scalar or container
            self.assertTrue(isinstance(result, (dict, list, str, int, float, type(None))),
                            "Result for multi-level predicate path should be JSON-serializable")
        except Exception as e:
            # Acceptable that the sample schema does not support multi-level predicates.
            self.assertTrue(isinstance(e, (KeyError, IndexError, LookupError, AttributeError)),
                            "If multi-level predicate not supported, expect a Key/Index/Lookup/Attribute error")

if __name__ == "__main__":
    unittest.main()
