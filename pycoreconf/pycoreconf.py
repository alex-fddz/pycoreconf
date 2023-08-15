# CORECONF Conversion library

from .sid import ModelSID
import json
import base64
import cbor2 as cbor


class ValueClass:
    """
    Wrapper class to encapsulate objects through the iteration
    """
    def __init__(self, value):
        self.value = value

def unwrapValues(object):
    """
    A function to unwrap Value objects properly, used by lookupSIDWithoutRecursion function
    """
    internalStack = [object]

    while internalStack:
        currentObject = internalStack.pop()

        if type(currentObject) == dict:
            keys = list(currentObject.keys())
            for key in keys:
                currentObject[key] = currentObject[key].value
                internalStack.append(currentObject[key])
        
        elif type(currentObject) == list:
            for i in range(len(currentObject)):
                currentObject[i] = currentObject[i].value
                internalStack.append(currentObject[i])

    return object

class CORECONFModel(ModelSID):
    """A class to represent the YANG Model through its SID file, used
    to convert to and from CORECONF/CBOR representation."""

    def __init__(self, 
                 sid_file, 
                 model_description_file=None):
        self.model_description_file = model_description_file
        self.yang_ietf_modules_paths = ["."]
        ModelSID.__init__(self, sid_file)

    def add_modules_path(self, path):
        """
        Config / Add a path or list of paths to yang ietf modules location.
        Required for decoded configuration data validation.
        """

        if type(path) is str:
            self.yang_ietf_modules_paths.append(path)
        elif type(path) is list:
            self.yang_ietf_modules_paths.extend(path)
        else:
            raise TypeError("Can only add path string or list of paths.")

    def _castDataTypes(self, obj, dtype, encoding):
        """
        Cast leaf value to correct Python data type according to YANG data type.
        """

        if type(dtype) is str:
            if dtype == "string":
                return str(obj)
            elif dtype in ["int8", "int16", "int32", "int64",
                            "uint8", "uint16", "uint32", "uint64"]:
                return int(obj)
            elif dtype == "decimal64":  # untested
                return float(obj)
            elif dtype == "binary":
                if encoding: 
                    dec = base64.b64decode(obj)
                    # return base64.b64encode(dec) # Nooo.
                    return dec
                else: 
                    enc = base64.b64encode(obj)
                    return enc.decode()
                    # return base64.b64decode(enc)
            elif dtype == "boolean":
                # ret = True if obj == "true" else False
                return bool(obj) 
            elif dtype == "inet:uri":
                return str(obj)
            elif dtype == "identityref": # look 'module:identity' in sids 
                if encoding:
                    idref_val = obj.split(":")
                    ref_mod, ref_id = idref_val[0], idref_val[1] # only supports 1 module for now
                    return self.sids[ref_id]
                else: # sid -> "module:identityref"
                    idref_val = self.name +":"+ self.ids[obj] 
                    return idref_val
            elif dtype in ["empty", "leafref", "instance-identifier", "bits"]: # just return obj
                # print("[-]", dtype, ": Returning as is." )
                return obj
            else:
                print("[X] Unrecognized obj type:", dtype, ". Returning as is.")
        elif type(dtype) is dict: # enumeration ({"value":"name"})
            if encoding: # inverse dict, w value as int
                dtype = {v: int(k) for k, v in dtype.items()}
            return dtype[str(obj)]
        elif type(dtype) is list: # union 
            print("[-] Union: Returning as is.")
            return obj
        return obj

    def lookupSID(self, obj, path="/", parent=0):
        """
        Look up SID for *obj* under *path*. 
        Dive in if it's a dictionary or a list of elements.
        > Deprecated for lookupSIDWithoutRecursion.
        """

        if type(obj) is dict:
            json_dict = {}
            for k, v in obj.items():
                element = path + k      # get full identifier path
                key = self.sids[element]     # look for SID value

                value = self.lookupSID(v, element+"/", key)  # dive in

                json_dict[key-parent] = value
            return json_dict

        elif type(obj) is list:
            json_list = []
            for e in obj:   # get each element of the list
                value = self.lookupSID(e, path, parent)  # dive in
                json_list.append(value)
            return json_list

        # Leaves:
        else:
            # get leaf data type according to model
            # and cast to correct data type.
            dtype = self.types[path[:-1]]
            return self._castDataTypes(obj, dtype, encoding=True)
            
    def lookupSIDWithoutRecursion(self, jsonData, path='/', parent=0):
        """
        a clone of lookupSID method which uses non recursive methods to compute SIDs and build the object
        """
        
        stack = [(ValueClass(jsonData), path, parent)]

        while stack:
            currentObject, currentPath, currentParent = stack.pop()
            currentValue  = currentObject.value

            # currentValue is a dict here, iterate through key/value pairs and add values to the stack
            if type(currentValue) == dict:
                keys = list(currentValue.keys())

                for key in keys:
                    qualifiedPath = currentPath + key
                    childSIDValue = self.sids[qualifiedPath]
                    sidDiff  = childSIDValue - currentParent
                    currentValue[sidDiff] = ValueClass(currentValue.pop(key))
                    stack.append((currentValue[sidDiff], qualifiedPath+"/", childSIDValue))
            
            # currentValue is a list type, append each of the object in currentValue to the stack
            elif type(currentValue) == list:
                for i in range(len(currentValue)):
                    currentValue[i] = ValueClass(currentValue[i])
                    stack.append((currentValue[i], currentPath, currentParent))
            
            # currentValue is a leaf here, transform their datatype 
            else:
                dtype = self.types[currentPath[:-1]]
                currentObject.value = self._castDataTypes(currentObject.value, dtype, encoding=True)
        
        # Unwrap the ValueClass objects before returning
        return(unwrapValues(jsonData))

    def toCORECONF(self, json_data):
        """
        Convert JSON data or file to CORECONF.
        """

        # Convert JSON data or file to Python Dictionary
        if json_data[-5:] == ".json":
            with open(json_data, 'r') as f:
                py_dict = json.load(f)
        else:
            py_dict = json.loads(json_data)

        # Transform to CORECONF/CBOR
        # valid = validateConfig(py_dict) #  ?
        cc = self.lookupSIDWithoutRecursion(py_dict)
        return cbor.dumps(cc)

    def lookupIdentifier(self, obj, delta=0, path="/"):
        """
        Look up leaf identifier for *obj* SID value. 
        Dive in if it's a dictionary or a list of elements.
        """

        if type(obj) is dict:
            json_dict = {}
            for k, v in obj.items():
                sid = k + delta             # get full identifier path
                identifier = self.ids[sid]       # look for SID value

                value = self.lookupIdentifier(v, sid, identifier)    # dive in

                json_dict[identifier.split("/")[-1]] = value
            return json_dict

        elif type(obj) is list:
            json_list = []
            for e in obj:   # get each element of the list
                value = self.lookupIdentifier(e, delta, path)    # dive in
                json_list.append(value)
            return json_list

        # Leaves:
        else:
            # get leaf data type according to model
            # and cast to correct data type.
            dtype = self.types[path]
            return self._castDataTypes(obj, dtype, encoding=False)

    def lookupIdentifierWithoutRecursion(self, obj, delta=0, path='/'):
        """
        A clone of lookupIdentifier method which uses non recursive methods to build the original JSON Object from SID represented Object
        """
        stack = [(ValueClass(obj), delta, path)]

        while stack:
            currentObject, currentDelta, currentPath = stack.pop()
            currentValue = currentObject.value

            # currentValue is a dict here, iterate through key/value pairs and add values to the stack
            if type(currentValue) is dict:
                keys = list(currentValue.keys())
                for key in keys:
                    # get full identifier path
                    
                    sid = key + currentDelta
                    # look for the original identifiers
                    identifier = self.ids[sid]
                    nodeIdentifier = identifier.split("/")[-1]
                    currentValue[nodeIdentifier] = ValueClass(currentValue.pop(key))
                    stack.append((currentValue[nodeIdentifier], sid, identifier))
        
            # currentValue is a list type, append each of the object in currentValue to the stack
            elif type(currentValue) is list:
                for i in range(len(currentValue)):
                    currentValue[i] = ValueClass(currentValue[i])
                    stack.append((currentValue[i], currentDelta, currentPath))

            # currentValue is a leaf here, transform their datatype before adding to the currentObject
            else:
                dtype = self.types[currentPath]
                currentObject.value = self._castDataTypes(currentObject.value, dtype, encoding=False)

        # Unwrap the ValueClass objects before returning
        return(unwrapValues(obj))

    def toJSON(self, cbor_data, return_pydict=False): 
        """
        Convert CORECONF (CBOR) data to JSON object (or Python dictionary).
        """

        data = cbor.loads(cbor_data)
        pyd = self.lookupIdentifierWithoutRecursion(data)
        valid = self.validateConfig(pyd)
        # + Option to directly save as file ?
        
        # Return JSON obj / pyDict
        return pyd if return_pydict else json.dumps(pyd) 

    def validateConfig(self, config):
        """
        Validate Python Dictionary config against module specification.
        Requires model description file and configured yang/ietf modules paths.
        """

        if self.model_description_file is None:
            # print("No model description file specified. Skipping validation.")
            return False
        from yangson import DataModel
        dm = DataModel.from_file(self.model_description_file, 
            self.yang_ietf_modules_paths)
        data = dm.from_raw(config)
        data.validate()
        # print("Config validation OK.")
        return True
