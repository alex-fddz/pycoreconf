#!/usr/bin/env python3
"""Regression tests for list-entry creation from an empty DB."""

import json
import os
import unittest

import pycoreconf


class TestEmptyDbListCreation(unittest.TestCase):
    def test_create_schc_rule_entry_from_empty_db(self):
        sid_path = os.path.join(
            os.path.dirname(__file__),
            "samples",
            "terraforma_test",
            "ietf-schc@2026-02-24.sid",
        )

        model = pycoreconf.CORECONFModel(sid_path)
        db = model.loadDB()

        xpath = "/schc/rule[rule-id-value='10'][rule-id-length='3']"
        db[xpath] = {}

        result = json.loads(db.to_json())
        self.assertIn("ietf-schc:schc", result)
        self.assertIn("rule", result["ietf-schc:schc"])

        rules = result["ietf-schc:schc"]["rule"]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["rule-id-value"], 10)
        self.assertEqual(rules[0]["rule-id-length"], 3)


if __name__ == "__main__":
    unittest.main()
