# CORECONF Conversion library

from .sid import ModelSID
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


class CORECONFDatabase:
    """
    High-level interface to navigate and modify CORECONF data using XPath-like paths.
    Usage: db["/measurements/measurement[type='solar-radiation'][id='0']/value"]
    """
    
    def __init__(self, model, cbor_data):
        """
        Initialize database from CORECONF model and CBOR data.
        
        Args:
            model: CORECONFModel instance
            cbor_data: CBOR-encoded data (bytes)
        """
        self.model = model
        self.data = cbor.loads(cbor_data) if isinstance(cbor_data, bytes) else cbor_data
    
    def _parse_xpath(self, xpath):
        """
        Parse XPath-like expression into segments and predicates.
        
        Args:
            xpath: string like "/measurements/measurement[type='solar-radiation'][id='0']/value"
        
        Returns:
            List of (segment_name, predicates_dict) tuples
            Example: [('measurements', {}), ('measurement', {'type': 'solar-radiation', 'id': '0'}), ('value', {})]
        """
        import re
        
        # Remove leading slash
        xpath = xpath.lstrip('/')
        
        # Split by / but keep predicates with their segment
        segments = []
        for part in xpath.split('/'):
            if not part:
                continue
            
            # Extract segment name and predicates
            # Format: segment[key1='value1'][key2='value2']
            match = re.match(r'^([^[]+)(.*)', part)
            if not match:
                continue
            
            segment_name = match.group(1).strip()
            predicates_str = match.group(2)
            
            # Parse predicates
            predicates = {}
            if predicates_str:
                pred_pattern = r"\[([^=]+)='([^']+)'\]"
                for pred_match in re.finditer(pred_pattern, predicates_str):
                    key_name = pred_match.group(1).strip()
                    key_value = pred_match.group(2).strip()
                    predicates[key_name] = key_value
            
            segments.append((segment_name, predicates))
        
        return segments
    
    def _resolve_path(self, xpath):
        """
        Resolve XPath to (target_sid, key_values).
        
        Args:
            xpath: XPath string
        
        Returns:
            (target_sid, list_of_key_values)
        """
        segments = self._parse_xpath(xpath)
        
        yang_path = ""
        key_values = []
        
        for segment_name, predicates in segments:
            # Build YANG path progressively
            if not yang_path:
                # Root element
                test_path = "/" + segment_name
                if test_path in self.model.sids:
                    yang_path = test_path
                else:
                    # Try with module prefix
                    for sid_path in self.model.sids.keys():
                        if sid_path.endswith(":" + segment_name):
                            yang_path = sid_path
                            break
                    if not yang_path:
                        raise KeyError(f"Root element not found: {segment_name}")
            else:
                # Child element
                test_path = yang_path + "/" + segment_name
                if test_path in self.model.sids:
                    yang_path = test_path
                else:
                    # Try with module prefix
                    found = False
                    for sid_path in self.model.sids.keys():
                        if sid_path.startswith(yang_path + "/") and (
                            sid_path.endswith(":" + segment_name) or 
                            sid_path == yang_path + "/" + segment_name
                        ):
                            yang_path = sid_path
                            found = True
                            break
                    if not found:
                        raise KeyError(f"Path element not found: {segment_name} (current: {yang_path})")
            
            # Handle predicates (list keys)
            if predicates:
                current_sid = self.model.sids[yang_path]
                
                # Check if this is a list node
                if str(current_sid) not in self.model.key_mapping:
                    raise ValueError(f"Predicates specified for non-list element: {segment_name}")
                
                expected_keys = self.model.key_mapping[str(current_sid)]
                
                # Resolve predicate names to SIDs and extract values in correct order
                for key_sid in expected_keys:
                    # Find the YANG path for this key SID
                    key_path = self.model.ids.get(key_sid)
                    if not key_path:
                        raise ValueError(f"Key SID not found in model: {key_sid}")
                    
                    # Extract leaf name (last part after /)
                    key_name = key_path.rstrip('/').split('/')[-1].split(':')[-1]
                    
                    if key_name not in predicates:
                        raise ValueError(f"Missing key predicate: {key_name}")
                    
                    # Get the value and convert type if needed
                    key_value = predicates[key_name]
                    
                    # Try to convert to appropriate type
                    # Check the data type from the model
                    if key_path in self.model.types:
                        dtype = self.model.types[key_path]
                        if isinstance(dtype, str):
                            if 'int' in dtype:
                                key_value = int(key_value)
                            elif dtype == 'identityref':
                                # Convert identity name to SID
                                identity_path = "/" + key_value if not key_value.startswith("/") else key_value
                                if identity_path in self.model.sids:
                                    key_value = self.model.sids[identity_path]
                                else:
                                    raise ValueError(f"Identity not found in model: {key_value}")
                    
                    key_values.append(key_value)
        
        target_sid = self.model.sids[yang_path]
        return target_sid, key_values
    
    def __getitem__(self, xpath):
        """
        Get value at XPath.
        Example: db["/measurements/measurement[type='solar-radiation'][id='0']/value"]
        """
        target_sid, keys = self._resolve_path(xpath)
        result = self.model.findSIDR(self.data, sid=target_sid, keys=keys)
        
        if result is None:
            raise KeyError(f"Path not found or keys don't match: {xpath}")
        
        # Unwrap the {sid: value} dict
        return result[target_sid]
    
    def __setitem__(self, xpath, value):
        """
        Set value at XPath.
        Example: db["/measurements/measurement[type='solar-radiation'][id='0']/value"] = 42
        """
        target_sid, keys = self._resolve_path(xpath)
        result = self.model.findSIDR(self.data, sid=target_sid, keys=keys, value=value)
        
        if result is None:
            raise KeyError(f"Path not found or keys don't match: {xpath}")
    
    def to_cbor(self):
        """Export modified data back to CBOR."""
        return cbor.dumps(self.data)
    
    def to_json(self):
        """Export data as JSON string."""
        return self.model.toJSON(self.to_cbor())


class CORECONFModel(ModelSID):
    """A class to represent the YANG Model through its SID file, used
    to convert to and from CORECONF/CBOR representation."""

    def __init__(self, 
                 sid_files: list[str], 
                 model_description_file: str = None):
        
        self.model_description_file = model_description_file
        self.yang_ietf_modules_paths = ["."]
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

    def findSID(self, obj, sid=None, keys= [], value= None, delta=0,  path='/'):
        """
        Find a specific SID in the object and return its value.
        """
        stack = [(ValueClass(obj), delta, path, keys)]

        while stack:
            currentObject, currentDelta, currentPath, currentKeys = stack.pop()
            currentValue = currentObject.value

            # currentValue is a dict here, iterate through key/value pairs and add values to the stack
            if type(currentValue) is dict:
                keys = list(currentValue.keys())
                for key in keys:
                    # get full identifier path
                    
                    p_sid = key + currentDelta
                    print(sid, p_sid, key, currentPath)
                    if sid is not None and sid == p_sid:
                        if value is None: # nothing to set, so return the value
                            found_value = currentValue[key]
                            print("Found SID:", sid, "with value:", found_value)
                            return {p_sid : found_value}
                        else: # set the value
                            currentValue[key] = value
                            print("Set SID:", sid, "to value:", value)
                            return {p_sid : value}

                    # look for the original identifiers
                    identifier = self.ids[p_sid]
                    nodeIdentifier = identifier.split("/")[-1]
                    child_object = currentValue.pop(key)

                    legacy_behavior = True # if True, will not check for list keys and will directly add the child object to the stack
                    if type (child_object) is dict and len(child_object) == 1: # one element, check if is a list by looking at key_mapping
                        child_key = next(iter(child_object))
                        
                        if str(child_key+key) in self.key_mapping: # we have a list so find the right entry in the list by comparing the provided keys with the keys of the entries in the list, then add the right entry to the stack
                            key_sids = self.key_mapping[str(child_key+key)]

                            if len(key_sids) > len(currentKeys):
                                raise ValueError("Not enough keys provided for list with key: " + str(child_key))
                            else:
                                first_key_values = currentKeys[:len(key_sids)]
                                new_keys = currentKeys[len(key_sids):]

                                match_keys = True
                                for entry in child_object[child_key]:

                                    for v, k_sid in zip(first_key_values, key_sids):
                                        entry_element = entry[k_sid-key-child_key]
                                        if entry_element != v:
                                            match_found = False
                                            break
                                        match_found = True
                                    
                                    if match_found:
                                        break

                                if match_found:
                                    recomposed_entry = {child_key+key : entry}
                                    stack.append((ValueClass(recomposed_entry), delta, identifier, new_keys))
                                    legacy_behavior = False
                                    break
                                else:
                                    return None # No match found for the provided keys in the list, return None or raise an exception as needed
                                    
                    if legacy_behavior: # not a list 
                        currentValue[nodeIdentifier] = ValueClass(child_object)
                        stack.append((currentValue[nodeIdentifier], p_sid, identifier, keys))
        
            # currentValue is a list type, append each of the object in currentValue to the stack
            elif type(currentValue) is list:
                print (currentValue)
                for i in range(len(currentValue)):

                    currentValue[i] = ValueClass(currentValue[i])
                    stack.append((currentValue[i], currentDelta, currentPath))

            # currentValue is a leaf here, transform their datatype before adding to the currentObject
            else:
                dtype = self.types[currentPath]
                currentObject.value = self._castDataTypes(currentObject.value, dtype, encoding=False)

        # Unwrap the ValueClass objects before returning
        return(unwrapValues(obj))

    def findSIDR(self, obj, sid=None, keys=None, value=None, delta=0, path='/'):
        """
        Recursive SID lookup/setter that preserves the tree structure.
        Returns {sid: value} when found, otherwise None.
        """

        if keys is None:
            keys = []

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
                                            return {p_sid: entry}
                                        entry.update(value) if isinstance(value, dict) else entry
                                        return {p_sid: entry}
                                    
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
                            return {p_sid: node[key]}
                        node[key] = value
                        return {p_sid: value}

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

    def loadDB(self, cbor_data):
        """
        Load CBOR data into a high-level database interface.
        
        Args:
            cbor_data: CBOR-encoded data (bytes)
        
        Returns:
            CORECONFDatabase instance for easy navigation and modification
        
        Example:
            db = model.loadDB(cbor_data)
            value = db["/measurements/measurement[type='solar-radiation'][id='0']/value"]
            db["/measurements/measurement[type='solar-radiation'][id='0']/value"] = 42
        """
        return CORECONFDatabase(self, cbor_data)
