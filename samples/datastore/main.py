#!/usr/bin/env python3
"""
Test program for coreconf-m2m model
Loads the SID file, generates random test data, and converts to CORECONF
"""

import sys
import os
import json
import random
import pprint


import pycoreconf

# Define transducer type identities (from the YANG model)
TRANSDUCER_TYPES = {
    "coreconf-m2m:solar-radiation": "W/m2",
    "coreconf-m2m:precipitation": "mm",
    "coreconf-m2m:air-temperature": "C",
    "coreconf-m2m:relative-humidity": "%",
    "coreconf-m2m:barometric-pressure": "kPa",
    "coreconf-m2m:vapor-pressure": "kPa",
    "coreconf-m2m:wind-speed": "m/s",
    "coreconf-m2m:wind-direction": "degrees",
    "coreconf-m2m:wind-gust": "m/s",
    "coreconf-m2m:strike-count": "count",
    "coreconf-m2m:average-distance": "km",
    "coreconf-m2m:tilt": "degrees"
}


def generate_random_transducer(transducer_type, unit):
    """Generate random transducer data based on type"""

    # Define realistic ranges for each transducer type
    ranges = {
        "coreconf-m2m:solar-radiation": (0, 1200),
        "coreconf-m2m:precipitation": (0, 50),
        "coreconf-m2m:air-temperature": (-40, 60),
        "coreconf-m2m:relative-humidity": (0, 100),
        "coreconf-m2m:barometric-pressure": (80, 110),
        "coreconf-m2m:vapor-pressure": (0, 5),
        "coreconf-m2m:wind-speed": (0, 25),
        "coreconf-m2m:wind-direction": (0, 360),
        "coreconf-m2m:wind-gust": (0, 40),
        "coreconf-m2m:strike-count": (0, 10),
        "coreconf-m2m:average-distance": (0, 50),
        "coreconf-m2m:tilt": (0, 90)
    }

    min_val, max_val = ranges.get(transducer_type, (0, 100))

    # Generate a random value and scale by precision
    raw_value = random.randint(int(min_val * 10), int(max_val * 10))
    precision = random.randint(0, 2)

    return {
        "type": transducer_type,
        "id": 0,
        "unit": unit,
        "precision": precision,
        "quantity": {
            "value": raw_value,
            "statistics": {
                "min": raw_value - random.randint(0, 50),
                "max": raw_value + random.randint(0, 50),
                "mean": raw_value - random.randint(-20, 20),
                "median": raw_value - random.randint(-15, 15),
                "stdev": random.randint(0, 100),
                "sample-count": random.randint(100, 10000)
            }
        }
    }

def generate_full_sequence_data():
    """Generate full test data with all available transducer types"""

    transducers = []
    for trans_type, unit in TRANSDUCER_TYPES.items():
        transducers.append(generate_random_transducer(trans_type, unit))

    config = {
        "coreconf-m2m:transducers": {
            "transducer": transducers
        }
    }

    return config


def main():
    """Main test function"""

    print("=" * 70)
    print("CORECONF M2M Weather Station CORECONF Test")
    print("=" * 70)

    # Path to the SID file
    sid_path = "coreconf-m2m@2026-03-29.sid"

    print(f"[DEBUG] SID path: {repr(sid_path)}")
    print(f"[DEBUG] Path exists: {os.path.exists(sid_path)}")
    print(f"[DEBUG] Is file: {os.path.isfile(sid_path)}")
    print(f"[DEBUG] Absolute path: {os.path.abspath(sid_path)}")

    if not os.path.exists(sid_path):
        print(f"ERROR: SID file not found at {sid_path}")
        sys.exit(1)

    print(f"\n[*] Loading SID file: {sid_path}")

    try:
        # Create the CORECONF model with the SID file
        ccm = pycoreconf.CORECONFModel(sid_path)
        print("[+] SID file loaded successfully")
    except Exception as e:
        print(f"[-] Error loading SID file: {e}")
        sys.exit(1)

    input("Press Enter to continue...")

    # Generate full test data (all transducer types)
    print("\n[*] Generating full test data (all transducer types)...")
    config_data = generate_full_sequence_data()
    print(f"[+] Test data generated ({len(config_data['coreconf-m2m:transducers']['transducer'])} transducers)")

    # Save to JSON file
    json_file = os.path.join(os.path.dirname(__file__), "generated_data.json")
    with open(json_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    print(f"[+] JSON data saved to: {json_file}")

    # Display the JSON data
    print("\n[*] Generated JSON configuration:")
    print("-" * 70)
    print(json.dumps(config_data, indent=2))
    print("-" * 70)
    print(f"[*] JSON size: {len(json.dumps(config_data))} characters")

    input("Press Enter to continue...")

    # Convert to CORECONF/CBOR
    print("\n[*] Converting to CORECONF/CBOR...")
    try:
        cbor_data = ccm.encode_json(json_file)
        print("[+] Conversion successful")
        print(f"[+] CBOR hex: {cbor_data.hex()}")
        print(f"[+] CBOR size: {len(cbor_data)} bytes")

        # Save CBOR data
        cbor_file = os.path.join(os.path.dirname(__file__), "generated_data.cbor")
        with open(cbor_file, 'wb') as f:
            f.write(cbor_data)
        print(f"[+] CBOR data saved to: {cbor_file}")
    except Exception as e:
        print(f"[-] Error converting to CORECONF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    input("Press Enter to continue...")

    # Try to decode back
    print("\n[*] Decoding CBOR back to JSON...")
    try:
        decoded_json = ccm.decode(cbor_data)
        print("[+] Decoding successful")
        print("\n[*] Decoded JSON configuration:")
        print("-" * 70)
        print(json.dumps(decoded_json, indent=2))
        print("-" * 70)

        # Compare original and decoded
        if json.dumps(config_data, sort_keys=True) == json.dumps(decoded_json, sort_keys=True):
            print("\n[+] SUCCESS: Original and decoded data match perfectly!")
        else:
            print("\n[!] WARNING: Original and decoded data differ")
            print("\nOriginal keys:", set(str(k) for k in config_data.keys()))
            print("Decoded keys: ", set(str(k) for k in decoded_json.keys()))

    except Exception as e:
        print(f"[-] Error decoding CBOR: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test new high-level datastore API
    print("\n" + "=" * 70)
    print("Testing CORECONFDatastore API (XPath-like syntax)")
    print("=" * 70)

    # Load CBOR data into datastore
    print("\n[*] Loading CBOR data into datastore...")
    ds = ccm.create_datastore_from_cbor(cbor_data)
    print("[+] Datastore loaded")

    # Test retrieving list keys for all transducer entries
    print("\n[*] Testing ds['/transducers/transducer'] to get full list of keys...")
    try:
        transducer_keys = ds["/transducers/transducer"]
        print(f"[+] Found {len(transducer_keys)} key set(s)")
        pprint.pprint(transducer_keys, width=200)
    except Exception as e:
        print(f"[-] Error reading keys: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test accessing the list entry (without leaf)
    xpath_entry = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']"
    print(f"\n[*] Reading entire list entry with XPath: {xpath_entry}")
    try:
        entry = ds[xpath_entry]
        print(f"[+] Complete entry retrieved:")
        pprint.pprint(entry, width=200)
    except Exception as e:
        print(f"[-] Error reading: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test reading sample-count (nested inside quantity/statistics)
    xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/quantity/statistics/sample-count"
    print(f"\n[*] Reading value with XPath: {xpath}")
    try:
        sample_count = ds[xpath]
        print(f"[+] sample-count = {sample_count}")
    except Exception as e:
        print(f"[-] Error reading: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test reading the current value (inside quantity)
    xpath_value = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/quantity/value"
    print(f"\n[*] Reading value with XPath: {xpath_value}")
    try:
        value = ds[xpath_value]
        print(f"[+] value = {value}")
    except Exception as e:
        print(f"[-] Error reading: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test reading precision (config leaf, directly on transducer)
    xpath_precision = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/precision"
    print(f"\n[*] Reading value with XPath: {xpath_precision}")
    try:
        precision = ds[xpath_precision]
        print(f"[+] precision = {precision}")

        # Calculate actual value
        if precision > 0:
            actual_value = value / (10 ** precision)
            print(f"[+] Actual value: {actual_value}")
    except Exception as e:
        print(f"[-] Error reading: {e}")

    input("Press Enter to continue...")

    # Test in-place increment operator (+=)
    print("\n[*] Testing in-place increment operator (+=)...")
    try:
        initial_count = ds[xpath]
        print(f"[+] Initial sample-count = {initial_count}")

        # Test += operator
        ds[xpath] += 1
        print(f"[+] Incremented with +=")

        verify_count = ds[xpath]
        print(f"[+] New sample-count = {verify_count}")

        if verify_count == initial_count + 1:
            print("[+] SUCCESS: += operator works!")
        else:
            print("[!] WARNING: += operator didn't work as expected")
    except Exception as e:
        print(f"[-] Error with += operator: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test that += fails on containers (non-leaf nodes)
    print("\n[*] Testing += on container (should fail)...")
    try:
        ds[xpath_entry] += 1  # Should fail: can't add int to dict
        print("[!] ERROR: += on container should have failed!")
    except TypeError as e:
        print(f"[+] Expected error caught: {type(e).__name__}")
        print(f"[+] Message: {e}")
    except Exception as e:
        print(f"[-] Unexpected error: {e}")

    input("Press Enter to continue...")

    # Test writing entire list entry with YANG representation
    print("\n[*] Writing complete list entry with YANG representation...")
    try:
        xpath_entry = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']"
        entry = ds[xpath_entry]
        original_entry = entry.copy()

        # Modify the entry - change unit and double precision
        entry['unit'] = 'kW/m²'  # Change unit
        entry['precision'] = entry['precision'] * 2  # Double precision

        print(f"[*] Original: unit='{original_entry['unit']}', precision={original_entry['precision']}")
        print(f"[*] Modified: unit='{entry['unit']}', precision={entry['precision']}")

        # Write the modified entry (YANG dict → CBOR)
        ds[xpath_entry] = entry
        print(f"[+] Entry written successfully")

        # Verify the write by reading back
        verified = ds[xpath_entry]
        print(f"[+] Verified: unit='{verified['unit']}', precision={verified['precision']}")

        if verified['unit'] == entry['unit'] and verified['precision'] == entry['precision']:
            print("[+] SUCCESS: Complete entry write confirmed!")
        else:
            print("[!] WARNING: Verified values differ from modified values")
    except Exception as e:
        print(f"[-] Error writing entry: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Export modified data
    print("\n[*] Exporting modified data...")
    try:
        modified_cbor = ds.to_cbor()
        print(f"[+] CBOR exported, size: {len(modified_cbor)} bytes")

        modified_json = ds.to_json()
        print("[+] JSON exported:")
        print("-" * 70)
        print(json.dumps(json.loads(modified_json), indent=2))
        print("-" * 70)
    except Exception as e:
        print(f"[-] Error exporting: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test creating a new list entry by setting a single leaf
    print("\n[*] Creating new list entry with single leaf assignment...")
    try:
        new_xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='1']"
        print(f"[*] Path to create: {new_xpath}")

        # Try to assign precision=3 to a non-existent entry
        ds[new_xpath] = {'precision': 3}  # Should create the entry with just the precision leaf
        print(f"[+] Assigned precision=3 to new entry")

        # Verify the assignment
        created_entry = ds[new_xpath]
        print(f"[+] Created entry = {created_entry}")

        if created_entry["precision"] == 3:
            print("[+] SUCCESS: New entry created with single leaf!")

            # Show the CBOR structure
            print("\n[*] CBOR structure after new entry creation:")
            print("-" * 70)
            cbor_bytes = ds.to_cbor()
            print(f"CBOR hex: {cbor_bytes.hex()}")
            print(f"CBOR size: {len(cbor_bytes)} bytes")
            print("-" * 70)

            # Convert to JSON
            print("\n[*] JSON representation after new entry creation:")
            print("-" * 70)
            json_output = ds.to_json()
            print(json.dumps(json.loads(json_output), indent=2))
            print("-" * 70)
        else:
            print("[!] WARNING: Precision value doesn't match")
    except Exception as e:
        print(f"[-] Error creating new entry: {e}")
        print(f"[-] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test deleting the precision field progressively
    print("\n[*] Step 1: Deleting precision field only...")
    try:
        precision_xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='1']/precision"
        del ds[precision_xpath]
        print(f"[+] Deleted precision field at {precision_xpath}")

        # Show JSON after deleting precision
        print("\n[*] JSON representation after deleting precision:")
        print("-" * 70)
        json_after_precision = ds.to_json()
        print(json.dumps(json.loads(json_after_precision), indent=2))
        print("-" * 70)
    except Exception as e:
        print(f"[-] Error deleting precision: {e}")
        print(f"[-] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test deleting the entire list entry
    print("\n[*] Step 2: Deleting the entire transducer node...")
    try:
        delete_xpath = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='1']"
        del ds[delete_xpath]
        print(f"[+] Deleted entry at {delete_xpath}")

        # Verify deletion by trying to read it (should fail)
        try:
            verify_deleted = ds[delete_xpath]
            print(f"[!] WARNING: Entry still exists!")
        except KeyError:
            print(f"[+] Verified: Entry successfully deleted")

        # Show JSON after deletion
        print("\n[*] JSON representation after deleting the transducer node:")
        print("-" * 70)
        final_json = ds.to_json()
        print(json.dumps(json.loads(final_json), indent=2))
        print("-" * 70)
    except Exception as e:
        print(f"[-] Error deleting entry: {e}")
        print(f"[-] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test incrementing all sample-counts via predicates()
    print("\n" + "=" * 70)
    print("Testing predicates() — increment all sample-counts by 1")
    print("=" * 70)
    try:
        for pred in ds.predicates("/transducers/transducer"):
            xpath_sc = f"/transducers/transducer{pred}/quantity/statistics/sample-count"
            ds[xpath_sc] += 1
            print(f"[+] {pred} → sample-count = {ds[xpath_sc]}")
        print("[+] SUCCESS: all sample-counts incremented")
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()

    input("Press Enter to continue...")

    # Test _resolve_path and its inverse _create_xpath
    print("\n" + "=" * 70)
    print("Testing _resolve_path() and _create_xpath() (round-trip)")
    print("=" * 70)
    try:
        xpath_in = "/transducers/transducer[type='coreconf-m2m:solar-radiation'][id='0']/quantity/statistics/sample-count"
        print(f"[*] Input XPath : {xpath_in}")

        target_sid, keys = ds._resolve_path(xpath_in)
        print(f"[+] _resolve_path → sid={target_sid}, keys={keys}")

        xpath_out = ds._create_xpath(target_sid, keys=keys)
        print(f"[+] _create_xpath → {xpath_out}")

        if xpath_in == xpath_out:
            print("[+] SUCCESS: round-trip XPath matches!")
        else:
            print(f"[!] Differs — in : {xpath_in}")
            print(f"[!]           out: {xpath_out}")
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
