# pycoreconf sample: "basic"
# This script demonstrates the basic usage of pycoreconf
#  using a simple YANG datamodel.

import pycoreconf

# Create the model object
ccm = pycoreconf.CORECONFModel("example-1@unknown.sid")

# Read JSON configuration file
config_file = "ex1-config.json"

with open(config_file, "r") as f:
    json_data = f.read()
print("Input JSON config data =\n", json_data, sep='')

# Convert configuration to CORECONF/CBOR
cbor_data = ccm.toCORECONF(config_file) # can also take json_data
print("Encoded CBOR data (CORECONF payload) =", cbor_data.hex())

# Decode CBOR data back to JSON configuration data
decoded_json = ccm.toJSON(cbor_data)
print("Decoded config data =", decoded_json)
