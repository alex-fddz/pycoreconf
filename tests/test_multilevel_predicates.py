#!/usr/bin/env python3
"""
Test XPath navigation avec prédicats à plusieurs niveaux.
"""
import json
import os

import pycoreconf

def main():
    print("=" * 70)
    print("Test: XPath with multiple predicate levels")
    print("=" * 70)
    
    # Load the SID and create the model
    sid_path = "../samples/terraforma/atmos-41-weather-station@2026-03-02.sid"
    
    if not os.path.exists(sid_path):
        print(f"[-] SID file not found at {sid_path}")
        return
    
    print(f"[*] Loading SID file: {sid_path}")
    ccm = pycoreconf.CORECONFModel(sid_path)
    print("[+] SID model loaded")
    
    # Load the CBOR test data
    cbor_path = "../samples/terraforma/test_data.cbor"
    print(f"[*] Loading CBOR data: {cbor_path}")
    
    with open(cbor_path, 'rb') as f:
        cbor_data = f.read()
    
    # Load into database
    db = ccm.create_database(cbor_data)
    print("[+] Database loaded")
    
    # Get the current JSON structure to understand it
    print("\n[*] Current JSON structure (first 50 lines):")
    json_output = db.to_json()
    json_lines = json_output.split('\n')[:50]
    for line in json_lines:
        print(line)
    
    # Test 1: Single-level predicate (already working)
    print("\n\n[*] TEST 1: Single-level predicate (baseline)")
    print("-" * 70)
    try:
        xpath1 = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/value"
        value1 = db[xpath1]
        print(f"[+] Path: {xpath1}")
        print(f"[+] Value: {value1}")
    except Exception as e:
        print(f"[-] Error: {e}")
    
    # Test 2: Two-level predicates (if the schema supports it)
    # This is a hypothetical case - let's check the actual structure
    
    print("\n\n[*] Inspecting if we can create a scenario with two predicate levels...")
    print("-" * 70)
    
    # First, let's understand the measurements structure
    try:
        measurements = db["/measurements"]
        if isinstance(measurements, dict):
            print("[+] /measurements is a container:")
            print(json.dumps(measurements, indent=2)[:500])
        elif isinstance(measurements, list):
            print(f"[+] /measurements is a list with {len(measurements)} items")
    except Exception as e:
        print(f"[-] Error reading measurements: {e}")
    
    # Try to understand the key structure
    print("\n\n[*] Analyzing key structure in the model...")
    print("-" * 70)
    try:
        # Access the model's key_mapping to understand which elements are lists
        if hasattr(db.model, 'key_mapping'):
            print(f"[+] Found {len(db.model.key_mapping)} list nodes in model")
            # Show a few examples
            count = 0
            for sid_str, key_sids in list(db.model.key_mapping.items())[:10]:
                print(f"    SID {sid_str}: keys = {key_sids}")
                count += 1
                if count >= 5:
                    print(f"    ... and {len(db.model.key_mapping) - 5} more")
                    break
    except Exception as e:
        print(f"[-] Error: {e}")
    
    # Test 3: Create a multi-level structure to test
    print("\n\n[*] TEST 3: Attempting to create nested list entries")
    print("-" * 70)
    
    # Try creating entries in a nested structure if it exists
    # First, let's see if there are any containers within measurements
    try:
        # Try to set a value deeper
        test_xpath = "/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']/value"
        current_value = db[test_xpath]
        print(f"[+] Successfully read at 1-level predicate: {current_value}")
        
        # Now try modifying it
        db[test_xpath] = current_value + 100
        print(f"[+] Successfully modified value to {current_value + 100}")
        
        # Read it back to verify
        new_value = db[test_xpath]
        print(f"[+] Verified new value: {new_value}")
        
        # Note about multi-level predicates
        print("\n[!] IMPORTANT NOTE:")
        print("[!] The current schema (atmos-41-weather-station) has a relatively flat structure")
        print("[!] Measurements is a list with keys [type, id], containing leaf fields")
        print("[!] To test truly multi-level predicates, we would need a schema with:")
        print("[!]   - Container A (with predicate keys)")
        print("[!]     - Container B (with predicate keys)")
        print("[!]       - Leaf fields")
        print("[!]")
        print("[!] The _resolve_path() and findSID() code SHOULD handle this correctly because:")
        print("[!]   1. _resolve_path() builds key_values list for each predicate in order")
        print("[!]   2. findSID() consumes keys as it descends through list nodes")
        print("[!]   3. remaining_keys are passed recursively to child nodes")
        
    except Exception as e:
        print(f"[-] Error in test 3: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Test completed")
    print("=" * 70)

if __name__ == "__main__":
    main()
