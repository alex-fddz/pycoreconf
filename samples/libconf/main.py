# pycoreconf sample: "libconfig"
# This script demonstrates the usage of pycoreconf
#  and how its output can be processed.

import pycoreconf
import libconf

def toLibconf(cfg_dict):
    """
    Convert a python dictionary to libconf data (.cfg).
    """
    cfg_str = str(cfg_dict) # Prep for libconf (pyTuple = liblist)
    cfg_str = cfg_str.replace("[", "libconf.LibconfList([").replace("]", "])")
    cfg_lc = eval(cfg_str) # back to dict
    return libconf.dumps(cfg_lc)

# Create the model object
ccm = pycoreconf.CORECONFModel("example-2@unknown.sid")

# Convert configuration to CORECONF/CBOR
config_file = "ex2-config.json"
cbor_data = ccm.toCORECONF(config_file) # can also take json_data

# Decode CBOR data to Python Dictionary
pyd = ccm.toJSON(cbor_data, return_pydict=True)

# Process and save to libconfig .cfg file
module_key = list(pyd.keys())[0] # Remove module key
cfg = toLibconf(pyd[module_key])

cfg_save_f = "config_data.cfg"
with open(cfg_save_f, 'w') as f:
    f.write(cfg)
print(f"Saved to {cfg_save_f}!")
