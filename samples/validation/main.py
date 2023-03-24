# pycoreconf sample: "basic"
# This script demonstrates the basic usage of pycoreconf
#  using a simple YANG datamodel.

import pycoreconf

# Create the model object (specify .sid and model description json file)
ccm = pycoreconf.CORECONFModel("example-4-a@unknown.sid", "description.json")
# Specify modules location for validation (or a list of paths):
ccm.add_modules_path("/home/alex/.local/share/yang/modules/ietf/")
ccm.add_modules_path(["/path/to/modules/", "another/path/"])

# Read JSON configuration file
config_file = "example-data.json"

# Convert configuration to CORECONF/CBOR
cbor_data = ccm.toCORECONF(config_file) 
print("Encoded CBOR data (CORECONF payload) =", cbor_data)

# Decode CBOR data back to JSON configuration data
decoded_json = ccm.toJSON(cbor_data)  # will validate the decoded config
print("Decoded config data =", decoded_json)
