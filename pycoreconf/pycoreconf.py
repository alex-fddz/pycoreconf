# CORECONF Conversion library

from .sid import ModelSID
from .datastore import CORECONFDatastore
import json
import base64
import cbor2 as cbor


class ConfigValidationError(Exception):
    """Raised when config validation fails; wraps the original exception."""
    pass


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
                 sid_files: list[str] | str, 
                 model_description_file: str = None):
        
        self.model_description_file = model_description_file
        self.yang_ietf_modules_paths = ["."]
        # Handle both single string and list of strings
        if isinstance(sid_files, str):
            sid_files = [sid_files]
        super().__init__(sid_files)

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
                # RFC 7951: int64/uint64 must be strings in JSON to avoid precision loss,
                # but CBOR uses native integers. Smaller types are safe as JSON numbers.
                if not encoding and dtype in ["int64", "uint64"]:
                    return str(obj)
                else:
                    return int(obj)
            elif dtype == "decimal64":
                # RFC 7951: decimal64 must be a string in JSON to avoid precision loss,
                # but CBOR can use a float or string representation
                if not encoding:
                    return str(obj)
                else:
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
            elif dtype == "identityref": # sid <-> 'module:identity'
                return self.sids[obj] if encoding else self.ids[obj]
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
            # print("[-] Union: Returning as is.")
            return obj

        # RFC 7951: Fallback for Decimal objects (e.g., from unrecognized typedefs)
        # Decimal values must be strings in JSON to maintain precision
        if not encoding:
            from decimal import Decimal
            if isinstance(obj, Decimal):
                return str(obj)

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

    def toCORECONF(self, config):
        """
        Convert JSON data, file, or dict to CORECONF.
        """

        # Work with a python dict
        if isinstance(config, dict):
            # "deepcopy"
            cfg_dict = json.loads(json.dumps(config))
        else:
            if config[-5:] == ".json":
                # Load the JSON file
                with open(config, 'r') as f:
                    cfg_dict = json.load(f)
            else:
                # Parse the JSON string
                cfg_dict = json.loads(config)

        # Attempt to validate the input config: python dict
        try:
            valid = self.validateConfig(cfg_dict) # valid -> validated or not
        except Exception as e:
            # Add context and preserve the original exception chain
            raise ConfigValidationError(f"Input config validation failed: {e}") from e

        # Transform to CORECONF/CBOR
        cc = self.lookupSIDWithoutRecursion(cfg_dict)

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

                json_key = identifier[len(path):].lstrip("/")
                json_dict[json_key] = value
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
                    nodeIdentifier = identifier[len(currentPath):].lstrip("/")
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

    def findSID(self, obj, sid=None, keys=None, value=None, delta=0, path='/', depth=None):
        """
        Recursive SID lookup/setter that preserves the tree structure.
        Returns {sid: value} when found, otherwise None.

        depth (int or None): maximum depth of the returned sub-tree.
            None / absent → full sub-tree (unbounded).
            0             → only direct scalar leaves, no nested containers.
            N             → N levels of nesting below the matched node.

        no_keys (bool): if True and the target SID is a list node, return all
            entries without requiring keys (CoMI keyless list discovery).
            Keys are always required when navigating *through* a list to reach
            a descendant node.
        """

        if keys is None:
            keys = []

        def _trim(node, d):
            """Trim a CBOR sub-tree to at most d levels of nesting."""
            if d is None:
                return node
            if isinstance(node, dict):
                if d == 0:
                    return {k: v for k, v in node.items()
                            if not isinstance(v, (dict, list))}
                return {k: _trim(v, d - 1) for k, v in node.items()}
            if isinstance(node, list):
                return [_trim(e, d) for e in node]
            return node

        def _walk(node, current_delta, current_path, remaining_keys):
            if type(node) is dict:
                for key in list(node.keys()):
                    p_sid = key + current_delta
                    identifier = self.ids[p_sid]
                    
                    # Check if this SID is a list key marker
                    if str(p_sid) in self.key_mapping:
                        # This is a list node, try to match keys
                        key_sids = self.key_mapping[str(p_sid)]
                        child_object = node[key]

                        # child_object is directly a list of dictionaries
                        if type(child_object) is list:
                            # Target IS the list node itself — return all entries if no_keys
                            if not keys and sid is not None and sid == p_sid:
                                return {p_sid: [_trim(e, depth) for e in child_object]}

                            if len(key_sids) > len(remaining_keys):
                                raise ValueError("Not enough keys provided for list with key: " + str(p_sid))

                            first_key_values = remaining_keys[:len(key_sids)]
                            new_keys = remaining_keys[len(key_sids):]

                            # Find matching list entry by comparing key values
                            for entry in child_object:
                                match_found = True
                                for expected_value, k_sid in zip(first_key_values, key_sids):
                                    entry_element = entry.get(k_sid - p_sid)
                                    if entry_element != expected_value:
                                        match_found = False
                                        break

                                if match_found:
                                    # If this is the target SID, return the matched entry
                                    if sid is not None and sid == p_sid:
                                        if value is None:
                                            return {p_sid: _trim(entry, depth)}
                                        entry.update(value) if isinstance(value, dict) else entry
                                        return {p_sid: _trim(entry, depth)}
                                    
                                    # Continue exploring within this entry
                                    result = _walk(entry, p_sid, identifier, new_keys)
                                    if result is not None:
                                        return result
                                    break
                        continue

                    # Regular node (not a list key)
                    # Check if we found the target SID
                    if sid is not None and sid == p_sid:
                        if value is None:
                            return {p_sid: _trim(node[key], depth)}
                        node[key] = value
                        return {p_sid: _trim(value, depth)}

                    # Regular node traversal
                    child_object = node[key]
                    result = _walk(child_object, p_sid, identifier, remaining_keys)
                    if result is not None:
                        return result

                return None

            if type(node) is list:
                for element in node:
                    result = _walk(element, current_delta, current_path, remaining_keys)
                    if result is not None:
                        return result
                return None

            return None

        return _walk(obj, delta, path, keys)

    def _create_xpath(self, sid, keys=None):
        """
        Convert a SID and optional key values to an XPath string.

        This is the inverse of CORECONFDatabase._resolve_path(): given the SID
        of a target node and the list of key values (in key_mapping order),
        reconstruct the XPath expression with predicates.

        Args:
            sid:  integer SID of the target node
            keys: list of key values in the same positional order as key_mapping
                  (same format as findSIDR's *keys* argument).
                  A flat list is expected; for nested lists the values must be
                  in path order (outermost list first).

        Returns:
            XPath string, e.g. "/container/list[key='val']/leaf"

        Raises:
            KeyError: if *sid* is not found in the model.

        Example:
            xpath = model._create_xpath(1234, keys=['solar-radiation', '0'])
            # → "/measurements/measurement[type='solar-radiation'][id='0']/value"
        """
        yang_path = self.ids.get(sid)
        if yang_path is None:
            raise KeyError(f"SID {sid} not found in model")

        segments = [s for s in yang_path.split('/') if s]
        xpath_parts = []
        current_path = ""
        key_index = 0
        keys = keys or []

        for segment in segments:
            # Strip module prefix: "ietf-foo:container" → "container"
            local_name = segment.split(':')[-1]
            current_path = current_path + "/" + segment

            seg_sid = self.sids.get(current_path)

            # If this segment is a list node, inject key predicates
            if seg_sid is not None and str(seg_sid) in self.key_mapping:
                key_sids = self.key_mapping[str(seg_sid)]
                predicates = []
                for key_sid in key_sids:
                    if key_index < len(keys):
                        key_path = self.ids.get(key_sid)
                        key_name = key_path.rstrip('/').split('/')[-1].split(':')[-1]
                        key_val = keys[key_index]
                        key_index += 1
                        # Identityref: numeric SID → resolve to "module:name"
                        key_type = self.types.get(key_path)
                        if isinstance(key_val, int):
                            if key_type == 'identityref':
                                resolved = self.ids.get(key_val)
                                if resolved:
                                    key_val = resolved
                            elif isinstance(key_type, dict):  # enum: {"0": "name", ...}
                                resolved = key_type.get(str(key_val))
                                if resolved:
                                    key_val = resolved
                        predicates.append(f"{key_name}='{key_val}'")
                if predicates:
                    xpath_parts.append(local_name + "".join(f"[{p}]" for p in predicates))
                else:
                    xpath_parts.append(local_name)
            else:
                xpath_parts.append(local_name)

        return "/" + "/".join(xpath_parts)


    def toJSON(self, cbor_data, return_pydict=False): 
        """
        Convert CORECONF (CBOR) data to JSON object (or Python dictionary).
        """

        data = cbor.loads(cbor_data)
        pyd = self.lookupIdentifierWithoutRecursion(data)

        # Attempt to validate the output config
        try:
            valid = self.validateConfig(pyd) # valid -> validated or not
        except Exception as e:
            # Add context and preserve the original exception chain
            raise ConfigValidationError(f"Output config validation failed: {e}") from e

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

    def create_datastore(self, cbor_data = cbor.dumps({})):
        """
        Load CBOR data into a high-level datastore interface.
        
        Args:
            cbor_data: CBOR-encoded data (bytes)
        
        Returns:
            CORECONFDatastore instance for easy navigation and modification
        
        Example:
            ds = model.create_datastore(cbor_data)
            value = ds["/measurements/measurement[type='solar-radiation'][id='0']/value"]
            ds["/measurements/measurement[type='solar-radiation'][id='0']/value"] = 42
        """
        return CORECONFDatastore(self, cbor_data)
