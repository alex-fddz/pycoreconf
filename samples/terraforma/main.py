#!/usr/bin/env python3
"""
Test program for terraforma ATMOS-41 weather station model
Loads the SID file, generates random test data, and converts to CORECONF
"""

import sys
import os
import json
import random
import pprint


import pycoreconf

# Define measurement type identities (from the YANG model)
MEASUREMENT_TYPES = {
    "atmos-41-weather-station:solar-radiation": "W/m2",
    "atmos-41-weather-station:precipitation": "mm",
    "atmos-41-weather-station:air-temperature": "C",
    "atmos-41-weather-station:relative-humidity": "%",
    "atmos-41-weather-station:barometric-pressure": "kPa",
    "atmos-41-weather-station:vapor-pressure": "kPa",
    "atmos-41-weather-station:wind-speed": "m/s",
    "atmos-41-weather-station:wind-direction": "degrees",
    "atmos-41-weather-station:wind-gust": "m/s",
    "atmos-41-weather-station:strike-count": "count",
    "atmos-41-weather-station:average-distance": "km",
    "atmos-41-weather-station:tilt": "degrees"
}


def generate_random_measurement(measurement_type, unit):
    """Generate random measurement data based on type"""
    
    # Define realistic ranges for each measurement type
    ranges = {
        "atmos-41-weather-station:solar-radiation": (0, 1200),
        "atmos-41-weather-station:precipitation": (0, 50),
        "atmos-41-weather-station:air-temperature": (-40, 60),
        "atmos-41-weather-station:relative-humidity": (0, 100),
        "atmos-41-weather-station:barometric-pressure": (80, 110),
        "atmos-41-weather-station:vapor-pressure": (0, 5),
        "atmos-41-weather-station:wind-speed": (0, 25),
        "atmos-41-weather-station:wind-direction": (0, 360),
        "atmos-41-weather-station:wind-gust": (0, 40),
        "atmos-41-weather-station:strike-count": (0, 10),
        "atmos-41-weather-station:average-distance": (0, 50),
        "atmos-41-weather-station:tilt": (0, 90)
    }
    
    min_val, max_val = ranges.get(measurement_type, (0, 100))
    
    # Generate a random value and scale by precision
    raw_value = random.randint(int(min_val * 10), int(max_val * 10))
    precision = random.randint(0, 2)
    
    return {
        "type": measurement_type,
        "id": 0,
        "value": raw_value,
        "precision": precision,
        "unit": unit,
        "min": raw_value - random.randint(0, 50),
        "max": raw_value + random.randint(0, 50),
        "mean": raw_value - random.randint(-20, 20),
        "median": raw_value - random.randint(-15, 15),
        "stdev": random.randint(0, 100),
        "sample-count": random.randint(100, 10000)
    }

def generate_full_sequence_data():
    """Generate full test data with all available measurement types"""

    measurements = []
    for meas_type, unit in MEASUREMENT_TYPES.items():
        measurements.append(generate_random_measurement(meas_type, unit))

    config = {
        "atmos-41-weather-station:measurements": {
            "measurement": measurements
        }
    }

    return config


def main():
    """Main test function"""
    
    print("=" * 70)
    print("TERRAFORMA Weather Station CORECONF Test")
    print("=" * 70)
    
    # Path to the SID file in terraforma
    sid_path = "atmos-41-weather-station@2026-03-02.sid"
    
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
    
    # Generate full test data (all measurement types)
    print("\n[*] Generating full test data (all measurement types)...")
    config_data = generate_full_sequence_data()
    print(f"[+] Test data generated ({len(config_data['atmos-41-weather-station:measurements']['measurement'])} measurements)")
    
    # Save to JSON file
    json_file = os.path.join(os.path.dirname(__file__), "test_data.json")
    with open(json_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    print(f"[+] JSON data saved to: {json_file}")

    # Display the JSON data
    print("\n[*] Generated JSON configuration:")
    print("-" * 70)
    print(json.dumps(config_data, indent=2))
    print("-" * 70)
    
    # Convert to CORECONF/CBOR
    print("\n[*] Converting to CORECONF/CBOR...")
    try:
        cbor_data = ccm.toCORECONF(json_file)
        print("[+] Conversion successful")
        print(f"[+] CBOR hex: {cbor_data.hex()}")
        print(f"[+] CBOR size: {len(cbor_data)} bytes")
        
        # Save CBOR data
        cbor_file = os.path.join(os.path.dirname(__file__), "test_data.cbor")
        with open(cbor_file, 'wb') as f:
            f.write(cbor_data)
        print(f"[+] CBOR data saved to: {cbor_file}")
    except Exception as e:
        print(f"[-] Error converting to CORECONF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Try to decode back
    print("\n[*] Decoding CBOR back to JSON...")
    try:
        decoded_json = ccm.toJSON(cbor_data)
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
    
    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70)

    # Test new high-level database API
    print("\n" + "=" * 70)
    print("Testing CORECONFDatabase API (XPath-like syntax)")
    print("=" * 70)
    
    # Load CBOR data into database
    print("\n[*] Loading CBOR data into database...")
    db = ccm.create_database(cbor_data)
    print("[+] Database loaded")

    # Test retrieving list keys for all measurement entries
    print("\n[*] Testing get_keys() on /measurements/measurement...")
    try:
        measurement_keys = db.get_keys("/measurements/measurement")
        print(f"[+] Found {len(measurement_keys)} key set(s)")
        pprint.pprint(measurement_keys, width=200)
    except Exception as e:
        print(f"[-] Error reading keys: {e}")
        import traceback
        traceback.print_exc()
    
    # Test accessing the list entry (without leaf)
    xpath_entry = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']"
    print(f"\n[*] Reading entire list entry with XPath: {xpath_entry}")
    try:
        entry = db[xpath_entry]
        print(f"[+] Complete entry retrieved:")
        pprint.pprint(entry, width=200)
    except Exception as e:
        print(f"[-] Error reading: {e}")
        import traceback
        traceback.print_exc()
    
    # Test reading a value with list keys
    # Note: 'type' is an identityref, so we use the identity name
    # 'id' is an integer
    xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/sample-count"
    print(f"\n[*] Reading value with XPath: {xpath}")
    try:
        sample_count = db[xpath]
        print(f"[+] sample-count = {sample_count}")
    except Exception as e:
        print(f"[-] Error reading: {e}")
        import traceback
        traceback.print_exc()
    
    # Test reading another value
    xpath_value = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/value"
    print(f"\n[*] Reading value with XPath: {xpath_value}")
    try:
        value = db[xpath_value]
        print(f"[+] value = {value}")
    except Exception as e:
        print(f"[-] Error reading: {e}")
        import traceback
        traceback.print_exc()
    
    # Test reading precision
    xpath_precision = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/precision"
    print(f"\n[*] Reading value with XPath: {xpath_precision}")
    try:
        precision = db[xpath_precision]
        print(f"[+] precision = {precision}")
        
        # Calculate actual value
        if precision > 0:
            actual_value = value / (10 ** precision)
            print(f"[+] Actual value: {actual_value}")
    except Exception as e:
        print(f"[-] Error reading: {e}")
    
    # Test in-place increment operator (+=)
    print("\n[*] Testing in-place increment operator (+=)...")
    try:
        initial_count = db[xpath]
        print(f"[+] Initial sample-count = {initial_count}")
        
        # Test += operator
        db[xpath] += 1
        print(f"[+] Incremented with +=")
        
        verify_count = db[xpath]
        print(f"[+] New sample-count = {verify_count}")
        
        if verify_count == initial_count + 1:
            print("[+] SUCCESS: += operator works!")
        else:
            print("[!] WARNING: += operator didn't work as expected")
    except Exception as e:
        print(f"[-] Error with += operator: {e}")
        import traceback
        traceback.print_exc()
    
    # Test that += fails on containers (non-leaf nodes)
    print("\n[*] Testing += on container (should fail)...")
    try:
        db[xpath_entry] += 1  # Should fail: can't add int to dict
        print("[!] ERROR: += on container should have failed!")
    except TypeError as e:
        print(f"[+] Expected error caught: {type(e).__name__}")
        print(f"[+] Message: {e}")
    except Exception as e:
        print(f"[-] Unexpected error: {e}")
    
    # Test writing entire list entry with YANG representation
    print("\n[*] Writing complete list entry with YANG representation...")
    try:
        xpath_entry = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']"
        entry = db[xpath_entry]
        original_entry = entry.copy()
        
        # Modify the entry - change unit and double precision
        entry['unit'] = 'kW/m²'  # Change unit
        entry['precision'] = entry['precision'] * 2  # Double precision
        
        print(f"[*] Original: unit='{original_entry['unit']}', precision={original_entry['precision']}")
        print(f"[*] Modified: unit='{entry['unit']}', precision={entry['precision']}")
        
        # Write the modified entry (YANG dict → CBOR)
        db[xpath_entry] = entry
        print(f"[+] Entry written successfully")
        
        # Verify the write by reading back
        verified = db[xpath_entry]
        print(f"[+] Verified: unit='{verified['unit']}', precision={verified['precision']}")
        
        if verified['unit'] == entry['unit'] and verified['precision'] == entry['precision']:
            print("[+] SUCCESS: Complete entry write confirmed!")
        else:
            print("[!] WARNING: Verified values differ from modified values")
    except Exception as e:
        print(f"[-] Error writing entry: {e}")
        import traceback
        traceback.print_exc()
    
    # Export modified data
    print("\n[*] Exporting modified data...")
    try:
        modified_cbor = db.to_cbor()
        print(f"[+] CBOR exported, size: {len(modified_cbor)} bytes")
        
        modified_json = db.to_json()
        print("[+] JSON exported:")
        print("-" * 70)
        print(json.dumps(json.loads(modified_json), indent=2))
        print("-" * 70)
    except Exception as e:
        print(f"[-] Error exporting: {e}")
        import traceback
        traceback.print_exc()
    
    # Test creating a new list entry by setting a single leaf
    print("\n[*] Creating new list entry with single leaf assignment...")
    try:
        new_xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='1']/precision"
        print(f"[*] Path to create: {new_xpath}")
        
        # Try to assign precision=3 to a non-existent entry
        db[new_xpath] = 3
        print(f"[+] Assigned precision=3 to new entry")
        
        # Verify the assignment
        verify_precision = db[new_xpath]
        print(f"[+] Verified precision = {verify_precision}")
        
        if verify_precision == 3:
            print("[+] SUCCESS: New entry created with single leaf!")
            
            # Show the CBOR structure
            print("\n[*] CBOR structure after new entry creation:")
            print("-" * 70)
            cbor_bytes = db.to_cbor()
            print(f"CBOR hex: {cbor_bytes.hex()}")
            print(f"CBOR size: {len(cbor_bytes)} bytes")
            print("-" * 70)
            
            # Convert to JSON
            print("\n[*] JSON representation after new entry creation:")
            print("-" * 70)
            json_output = db.to_json()
            print(json.dumps(json.loads(json_output), indent=2))
            print("-" * 70)
        else:
            print("[!] WARNING: Precision value doesn't match")
    except Exception as e:
        print(f"[-] Error creating new entry: {e}")
        print(f"[-] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    # Test deleting the precision field progressively
    print("\n[*] Step 1: Deleting precision field only...")
    try:
        precision_xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='1']/precision"
        del db[precision_xpath]
        print(f"[+] Deleted precision field at {precision_xpath}")
        
        # Show JSON after deleting precision
        print("\n[*] JSON representation after deleting precision:")
        print("-" * 70)
        json_after_precision = db.to_json()
        print(json.dumps(json.loads(json_after_precision), indent=2))
        print("-" * 70)
    except Exception as e:
        print(f"[-] Error deleting precision: {e}")
        print(f"[-] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    # Test deleting the entire list entry
    print("\n[*] Step 2: Deleting the entire measurement node...")
    try:
        delete_xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='1']"
        del db[delete_xpath]
        print(f"[+] Deleted entry at {delete_xpath}")
        
        # Verify deletion by trying to read it (should fail)
        try:
            verify_deleted = db[delete_xpath]
            print(f"[!] WARNING: Entry still exists!")
        except KeyError:
            print(f"[+] Verified: Entry successfully deleted")
        
        # Show JSON after deletion
        print("\n[*] JSON representation after deleting the measurement node:")
        print("-" * 70)
        final_json = db.to_json()
        print(json.dumps(json.loads(final_json), indent=2))
        print("-" * 70)
    except Exception as e:
        print(f"[-] Error deleting entry: {e}")
        print(f"[-] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Database API test completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()
