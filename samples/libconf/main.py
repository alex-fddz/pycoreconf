# pycoreconf sample: "libconfig"
# This script demonstrates the usage of pycoreconf and how its output can be
# processed.

import pycoreconf

try:
    import libconf
except ImportError:
    print("To run this sample, install libconf: pip install libconf")
    exit()

def dict_to_libconf(cfg_dict):
    """
    Convert a python dictionary to libconf data (.cfg).
    """
    cfg_str = str(cfg_dict) # Prep for libconf (pyTuple = liblist)
    cfg_str = cfg_str.replace("[", "libconf.LibconfList([").replace("]", "])")
    cfg_lc = eval(cfg_str) # back to dict
    return libconf.dumps(cfg_lc)

# Create the model object
ccm = pycoreconf.CORECONFModel("example-2.sid")

# Convert configuration to CORECONF/CBOR
config_file = "ex2-config.json"
cbor_data = ccm.encode_json(config_file)

print(f"Encoded data: {cbor_data.hex()}")

# Decode CBOR data to Python Dictionary
pyd = ccm.decode(cbor_data)

# Process and save to libconfig .cfg file
module_key = list(pyd.keys())[0] # Remove module key
cfg = dict_to_libconf(pyd[module_key])

cfg_save_f = "generated_data.cfg"
with open(cfg_save_f, 'w') as f:
    f.write(cfg)
print(f"\nDecoded config saved to {cfg_save_f}!")
