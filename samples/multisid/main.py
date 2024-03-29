# pycoreconf sample: "basic"
# This script demonstrates the basic usage of pycoreconf
#  using multiple sid file definitions.

import pycoreconf

# Create the model object (specify .sid and model description json file)
ccm = pycoreconf.CORECONFModel("ietf-schc@2023-01-28.sid", 
                               "ietf-schc-oam@2021-11-10.sid",
                               model_description_file="description.json")
# Specify modules location for validation (or a list of paths):
ccm.add_modules_path("/home/alex/Projects/pyang/modules/ietf/")
ccm.add_modules_path(["/path/to/modules/", "another/path/"])

# Read JSON configuration file
config_file = "schc.json"

# Convert configuration to CORECONF/CBOR
cbor_data = ccm.toCORECONF(config_file) 
print("Encoded CBOR data (CORECONF payload) =", cbor_data.hex())

# Decode CBOR data back to JSON configuration data
decoded_json = ccm.toJSON(cbor_data)  # will validate the decoded config
print("Decoded config data =", decoded_json)
