# pycoreconf sample: "basic"
# This script demonstrates the core encode/decode workflow using pycoreconf:
#   1. encode_json(): JSON string -> CORECONF (CBOR)
#   2. decode(): CORECONF -> Python dict (native types)
#   3. encode(): Python dict -> CORECONF
#   4. decode_to_json(): CORECONF -> JSON string (RFC 7951-compliant)

import pycoreconf
import json

# Create the model object
ccm = pycoreconf.CORECONFModel("example-1.sid")

# Read JSON configuration file
config_file = "ex1-config.json"
with open(config_file, "r") as f:
    json_config = f.read()

print(f"Input JSON config data ({len(json_config)} B):\n{json_config}")

# Encode the JSON config to CORECONF/CBOR
cbor_data = ccm.encode_json(json_config) # or config_file
print(f"Encoded CBOR data (CORECONF payload): {cbor_data.hex()}" \
    f" ({len(cbor_data)} B)")

# Decode CBOR data back to Python dictionary
config = ccm.decode(cbor_data)
print(f"\nDecoded config (Python dict): {config}")

assert config == json.loads(json_config)
print("\nDecoded config matches exactly!")

# Modify the configuration (native dict manipulation)
config["example-1:greeting"]["message"] = "General Kenobi!"
config["example-1:greeting"]["author"] = "G."
print(f"\nModified config: {config}")

# Re-encode the modified config to CORECONF
new_cbor_data = ccm.encode(config)
print(f"\nRe-encoded CBOR data: {new_cbor_data.hex()}" \
    f" ({len(new_cbor_data)} B)")

# Decode the modified config to verify
final_config = ccm.decode_to_json(new_cbor_data)
print(f"\nFinal JSON config: {final_config}" \
    f" ({len(final_config)} B)")

assert json.loads(final_config) == config
print("\nDecoded config matches exactly!")
