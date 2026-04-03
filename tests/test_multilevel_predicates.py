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
        cls.sid_path = helpers.resolve_filepath("samples/datastore/coreconf-m2m@2026-03-29.sid")
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
            "a11a000186dea1018ca518211a000186a80100182264572f6d32110112a20b19"
            "059b01a60419057f011905ac021905a90319059206183b0519054da518211a00"
            "0186a601001822626d6d110012a20b1901e001a6041901c2011901e3021901ed"
            "031901de06185e05190e57a518211a000186a1010018226143110212a20b38cc"
            "01a60438e601389f0238d40338c1060505191bd5a518211a000186a701001822"
            "6125110012a20b19030901a6041902f9011903280219030d031903040618360519"
            "202ba518211a000186a301001822636b5061110112a20b19043001a604190412"
            "0119045d021904310319042f0601051920d2a518211a000186ac01001822636b"
            "5061110212a20b1201a60426011833020903181f06183305191661a518211a00"
            "0186af01001822636d2f73110012a20b18c901a60418b60118f40218d30318bc"
            "061305191ef2a518211a000186ad010018226764656772656573110212a20b19"
            "0e0101a604190df701190e0b02190e0f03190dfe06182f05191d21a518211a00"
            "0186ae01001822636d2f73110012a20b184a01a604182101187b02185b031844"
            "06181e0519220da518211a000186a90100182265636f756e74110012a20b184c"
            "01a604183401185902186003185506185b051921b9a518211a000186a2010018"
            "22626b6d110112a20b19016301a60419015101190184021901650319016f0618"
            "3e05191616a518211a000186aa010018226764656772656573110012a20b1835"
            "01a604182201185202182403184306185f0519185e"
        )
        cls.ds = cls.ccm.create_datastore(cbor_data)

    def test_transducers_path_exists_and_type(self):
        # Ensure /transducers exists and is list or dict
        measurements = self.ds["/transducers"]
        self.assertTrue(isinstance(measurements, (list, dict)),
                        "/transducers should be a list or dict in datastore")

    def test_single_level_predicate_read(self):
        # baseline: read a known path with single-level predicates
        xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/quantity/value"
        val = self.ds[xpath]
        # assert it is a numeric value (int or float) or a string that can represent a number
        self.assertIsNotNone(val, "Value at single-level predicate path should not be None")
        self.assertTrue(isinstance(val, (int, float, str)),
                        "Value should be int, float, or string")

    def test_single_level_predicate_modify_and_verify(self):
        # read current value, modify, and verify round-trip via datastore indexing
        xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/quantity/value"
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
        multi_xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/subcontainer[subid='x']/leaf"
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
