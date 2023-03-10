# CORECONF Conversion library

from .sid import ModelSID
import json
import base64
import cbor2 as cbor
import libconf

policy_t = {
    "protect" : 0,
    "bypass" : 1,
    "discard" : 2
}

policy_t_dict = {v: k for k, v in policy_t.items()}

class CCModel(ModelSID):
    def __init__(self, 
                 sid_file, 
                 model_description_file=None):
        self.model_description_file = model_description_file
        self.yang_ietf_modules_paths = ["."]
        ModelSID.__init__(self, sid_file)
        self.sids, self.types = ModelSID.getSIDsAndTypes(self) #req. ltn22/pyang

    def add_modules_path(self, path):
        """
        Config / Add a path or list of paths to yang ietf modules location.
        """
        if type(path) is str:
            self.yang_ietf_modules_paths.append(path)
        elif type(path) is list:
            self.yang_ietf_modules_paths.extend(path)
        else:
            raise TypeError("Can only add path string or list of paths.")

def lookupSID(obj, path, parent=0):
    """
    Look up SID for *obj* under *path*. Dive in if it's a dictionary or a list of elements.
    """

    if type(obj) is dict:
        json_dict = {}
        for k, v in obj.items():
            element = path + k      # get full identifier path
            key = sids[element]     # look for SID value

            value = lookupSID(v, element+"/", key)  # dive in

            json_dict[key-parent] = value
        return json_dict

    elif type(obj) is list:
        json_list = []
        for e in obj:   # get each element of the list
            value = lookupSID(e, path, parent)  # dive in
            json_list.append(value)
        return json_list

    # Leaves:
    else:
        # get leaf data type according to model
        # and cast to correct data type.
        dtype = types[path[:-1]]

        if dtype == "string":
            return str(obj)
        elif dtype == "uint32":
            return int(obj)
        elif dtype == "binary":
            dec = base64.b64decode(obj)
            return base64.b64encode(dec)
        elif dtype == "inet:uri":
            return str(obj)
        elif dtype == "policy-t":
            # return obj
            return policy_t[obj]
        else:
            print(" X unrecognized obj type.")
            print(path, dtype)
            return obj

def toCORECONF(data):
    """
    Convert JSON data to CORECONF.
    """
    cc = lookupSID(data, "/")
    return cc


def lookupIdentifier(obj, delta=0, path="/"):
    """
    Look up leaf identifier for *obj* SID value. Dive in if it's a dictionary or a list of elements.
    """

    if type(obj) is dict:
        json_dict = {}
        for k, v in obj.items():
            sid = k + delta             # get full identifier path
            identifier = ids[sid]       # look for SID value

            value = lookupIdentifier(v, sid, identifier)    # dive in

            json_dict[identifier.split("/")[-1]] = value
        return json_dict

    elif type(obj) is list:
        json_list = []
        for e in obj:   # get each element of the list
            value = lookupIdentifier(e, delta, path)    # dive in
            json_list.append(value)
        return json_list

    # Leaves:
    else:
        # get leaf data type according to model
        # and cast to correct data type.
        dtype = types[path]

        if dtype == "string":
            return str(obj)
        elif dtype == "uint32":
            return int(obj)
        elif dtype == "binary":
            return obj.decode()
            # enc = base64.b64encode(obj)
            # return base64.b64decode(enc)
        elif dtype == "inet:uri":
            return str(obj)
        elif dtype == "policy-t":
            # return obj
            return policy_t_dict[obj]
        else:
            print(" X unrecognized obj type.")
            print(path, dtype)
            return obj

def toJSON(data): # toPyDict
    """
    Convert CORECONF/CBOR data to JSON (python dictionary).
    """
    cfg = lookupIdentifier(data) # dict
    jsn = json.dumps(cfg) # json
    return cfg

def toLibconf(cfg_dict):
    """
    Convert a python dictionary to libconf data (.cfg).
    """
    # Prep for libconf (pyTuple = liblist)
    cfg_str = str(cfg_dict)
    cfg_str = cfg_str.replace("[", "libconf.LibconfList([").replace("]", "])")
    # Convert to libconf
    cfg_lc = eval(cfg_str) # convert back to dict
    return libconf.dumps(cfg_lc)

def validateJSON(config, desc_file, modules_paths=["."]):
    """
    Validate JSON config against module specification.
    Requires model description file and configured modules paths.
    """
    if desc_file is None:
        print("No model description file provided. Skipping validation.")
        return
    from yangson import DataModel
    dm = DataModel.from_file(desc_file, 
        modules_paths)
    data = dm.from_raw(config)
    data.validate()
    print("Config validation OK.")


def js2cc(json_file, sid_file=None):
    """
    Match SID file + JSON config data to generate CORECONF (CBOR) & save as file.
    """

    print(f"Generating CORECONF from {json_file} (+{sid_file}):")

    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    sid_file = default_model_sid_file if sid_file is None else sid_file

    # Retrieve SIDs & data types from SID file
    global sids, types
    sids, types = getSIDsAndTypes(sid_file)

    # Read the contents of the json config file
    with open(json_file, "r") as f:
        obj = json.load(f)

    # Convert and pretty-print
    pp.pprint(obj)
    cc = toCORECONF(obj)
    pp.pprint(cc)

    # Dump CORECONF data as CBOR
    cb = cbor.dumps(cc)
    print("Size in CBOR =", len(cb))

    # Save to file
    fname = json_file[:-4]+"cbor"
    with open(fname, "wb") as bf:
        bf.write(cb)

    print(f"Done! Saved to {fname}.")

def cc2cfg(cbor_file, sid_file=None):
    """
    Match SID file + CORECONF (CBOR) config data to generate libconfig (.cfg) & save as file.
    """

    print(f"Generating libconfig from {cbor_file} (+{sid_file}):")

    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    sid_file = default_model_sid_file if sid_file is None else sid_file

    # Retrieve IDs & data types from SID file
    global ids, types #, sids
    sids, types = getSIDsAndTypes(sid_file)
    # Inverse sids = {sid:identifier}
    ids = {v: k for k, v in sids.items()}
    # or: ids = getIdentifiers(sid_file)
    # pp.pprint(ids)

    # Read the contents of the CORECONF/CBOR file
    with open(cbor_file, "rb") as f:
        cc = cbor.load(f) # dict

    # Convert and pretty-print
    pp.pprint(cc)
    jsn = toJSON(cc)
    pp.pprint(jsn)

    # Validate config
    validateJSON(jsn, model_description_file, yang_ietf_modules_paths)

    # Generate libconf .cfg file
    cfg = toLibconf(jsn)
    print(cfg)

    # Save to file
    fname = cbor_file[:-4]+"cfg"
    with open(fname, "w") as f:
        f.write(cfg)

    print(f"Done! Saved to {fname}.")

def json_to_coreconf(config_file, sid_file=None):
    """
    Minimal function; to use in coap_post.py
    """
    global sids, types
    sid_file = default_model_sid_file if sid_file is None else sid_file
    sids, types = getSIDsAndTypes(sid_file)
    with open(config_file, "r") as f:
        obj = json.load(f) # read json config file
    cc = toCORECONF(obj)
    return cbor.dumps(cc)

def coreconf_to_libconf(cbor_data, save_loc, sid_file=None):
    """
    Minimal function; to use in coap_server.py
    """
    global ids, types
    sid_file = default_model_sid_file if sid_file is None else sid_file
    sids, types = getSIDsAndTypes(sid_file)
    ids = {v: k for k, v in sids.items()}
    jsn = toJSON(cbor_data)
    validateJSON(jsn, model_description_file, yang_ietf_modules_paths)
    #TODO: remove parent key (module name)
    cfg = toLibconf(jsn)
    # Save as file
    with open(save_loc, "w") as f:
        f.write(cfg)
    print("Saved config to", save_loc)


def set_sid_file(sid_file):
    """
    DEPRECATED.
    Config / Set default model SID file.
    """
    global default_model_sid_file
    # Check file exists
    with open(sid_file, 'r') as f:
        default_model_sid_file = sid_file

def set_description_file(desc_file):
    """
    DEPRECATED.
    Config / Set default model description file.
    """
    global model_description_file
    # Check file exists
    with open(desc_file, 'r') as f:
        model_description_file = desc_file