# pycoreconf sample: "multisid"
# This script demonstrates the basic usage of pycoreconf
#  using multiple yang models / sid file definitions.

import pycoreconf
import json

# Create the model object with multiple SID files
ccm = pycoreconf.CORECONFModel(
    [
        "ietf-schc@2023-01-28.sid",
        "ietf-schc-oam@2021-11-10.sid"
    ]
)

# Read JSON configuration file
config_file = "schc.json"

# Convert configuration to CORECONF/CBOR
cbor_data = ccm.encode_json(config_file) 
print(f"Encoded CBOR data (CORECONF payload) = {cbor_data.hex()}" \
    f" ({len(cbor_data)})")

# Decode CBOR data back to JSON configuration data
decoded_json = ccm.decode_to_json(cbor_data)
# print("\nDecoded config data =", decoded_json, "\n")

# Test
with open(config_file, "r") as f:
    original_json = json.load(f)
assert original_json == json.loads(decoded_json)
print(f"\nDecoded JSON (size = {len(decoded_json)}) matches input config perfectly!")
