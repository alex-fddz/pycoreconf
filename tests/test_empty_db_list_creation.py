#!/usr/bin/env python3
"""Regression tests for list-entry creation from an empty datastore."""

import unittest
import json
import helpers

import pycoreconf


class TestEmptyStoreListCreation(unittest.TestCase):
    def test_create_schc_rule_entry_from_empty_store(self):
        sid_path = helpers.resolve_filepath("samples/terraforma/ietf-schc@2026-02-24.sid")

        model = pycoreconf.CORECONFModel(sid_path)
        ds = model.create_datastore()

        xpath = "/schc/rule[rule-id-value='10'][rule-id-length='3']"
        ds[xpath] = {}

        result = json.loads(ds.to_json())
        self.assertIn("ietf-schc:schc", result)
        self.assertIn("rule", result["ietf-schc:schc"])

        rules = result["ietf-schc:schc"]["rule"]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["rule-id-value"], 10)
        self.assertEqual(rules[0]["rule-id-length"], 3)


if __name__ == "__main__":
    unittest.main()
