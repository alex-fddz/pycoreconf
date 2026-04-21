# pycoreconf sample: "validation"
# This script demonstrates how a configuration may be validated against its
# YANG data model.

import pycoreconf

# Create the model object (specify .sid and model description json file)
ccm = pycoreconf.CORECONFModel("example-4-a.sid", model_description_file="description.json")

# Specify modules location for validation (or a list of paths):
ccm.add_modules_path("ietf/")
ccm.add_modules_path(["/path/to/modules/", "another/path/"])

# Read JSON configuration file
config_file = "example-data.json"
json_config = open(config_file, "r", encoding="utf-8").read()
print(f"Input JSON config = {json_config}")

# Validate the RFC7951-compliant input configuration:
ccm.validate_json(json_config) # raises an error if not valid.
print("Input JSON is valid!")

# Convert configuration to CORECONF/CBOR
cbor_data = ccm.encode_json(json_config)
print(f"Encoded CBOR data (CORECONF payload) = {cbor_data.hex()}")

# Decode CBOR data back to JSON configuration data
decoded_json = ccm.decode_to_json(cbor_data)
print(f"Decoded config data = {decoded_json}")

#validate the decoded config
ccm.validate_json(decoded_json)
print("Decoded JSON is valid!")
