#!/usr/bin/env python3
"""
Test program for terraforma ATMOS-41 weather station model
Loads the SID file, generates random test data, and converts to CORECONF
"""

import sys
import os
import json
import random
from datetime import datetime

# Add parent directory to path to import pycoreconf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

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
        "id": random.randint(0, 3),  # Multiple sensor instances
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


def generate_test_data():
    """Generate random test data following the ATMOS-41 model"""
    
    # Select random measurements to include
    num_measurements = random.randint(3, 8)
    selected_types = random.sample(list(MEASUREMENT_TYPES.items()), num_measurements)
    
    measurements = []
    for meas_type, unit in selected_types:
        measurements.append(generate_random_measurement(meas_type, unit))
    
    # Create the complete configuration with proper module prefix
    # The JSON keys must match the SID structure exactly:
    # /atmos-41-weather-station:measurements
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
    sid_path = "/Users/laurent/work/terraforma/atmos-41-weather-station@2026-03-02.sid"
    
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
    
    # Generate random test data
    print("\n[*] Generating random test data...")
    config_data = generate_test_data()
    print("[+] Test data generated")
    
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


if __name__ == "__main__":
    main()
