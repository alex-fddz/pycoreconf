#!/usr/bin/env python3
"""Unit tests for CORECONFDatabase.get_keys()."""

import os
import unittest

import pycoreconf


class TestGetKeys(unittest.TestCase):
    def test_get_keys_on_measurement_list(self):
        sid_path = os.path.join(
            os.path.dirname(__file__),
            "samples",
            "terraforma_test",
            "atmos-41-weather-station@2026-03-02.sid",
        )

        model = pycoreconf.CORECONFModel(sid_path)
        db = model.loadDB()

        db["/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']"] = {}
        db["/measurements/measurement[type='atmos-41-weather-station:wind-speed'][id='1']"] = {}

        keys = db.get_keys("/measurements/measurement")

        self.assertIsInstance(keys, list)

        expected = [
            "[type='atmos-41-weather-station:solar-radiation'][id='0']",
            "[type='atmos-41-weather-station:wind-speed'][id='1']",
        ]
        self.assertCountEqual(keys, expected)

    def test_get_keys_with_predicates(self):
        sid_path = os.path.join(
            os.path.dirname(__file__),
            "samples",
            "terraforma_test",
            "atmos-41-weather-station@2026-03-02.sid",
        )

        model = pycoreconf.CORECONFModel(sid_path)
        db = model.loadDB()

        keys = db.get_keys(
            "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='2']"
        )

        self.assertEqual(
            keys,
            ["[type='atmos-41-weather-station:solar-radiation'][id='2']"],
        )


if __name__ == "__main__":
    unittest.main()
