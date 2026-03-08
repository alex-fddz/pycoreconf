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
                                # Try without leading slash first
                                if key_value in self.model.sids:
                                    key_value = self.model.sids[key_value]
                                else:
                                    # Try with leading slash
                                    identity_path = "/" + key_value
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
        Returns values with YANG identifiers instead of SIDs.
        """
        import copy
        
        # Resolve the path
        target_sid, keys = self._resolve_path(xpath)
        target_path = self.model.ids.get(target_sid, '')
        
        # Check if this is a leaf (has type info in model)
        is_leaf = target_path in self.model.types
        
        # If it's a leaf and we're accessing it directly, get parent value and extract leaf
        if is_leaf and keys:
            # This is a leaf within a list entry
            # Get the parent container instead
            parent_path = '/'.join(target_path.split('/')[:-1])
            parent_sid = self.model.sids.get(parent_path)
            
            if parent_sid:
                result = self.model.findSIDR(self.data, sid=parent_sid, keys=keys)
                if result is None:
                    raise KeyError(f"Path not found or keys don't match: {xpath}")
                
                value = result[parent_sid]
                
                if '/' in parent_path:
                    parent_parent_path = '/'.join(parent_path.split('/')[:-1]) + '/'
                else:
                    parent_parent_path = '/'
                
                value_copy = copy.deepcopy(value)
                wrapped = {parent_sid: value_copy}
                self.model.lookupIdentifierWithoutRecursion(wrapped, delta=0, path=parent_parent_path)
                
                node_identifier = parent_path.split('/')[-1]
                entry = wrapped.get(node_identifier, value_copy)
                
                # Extract the leaf from the entry
                leaf_key = target_path.split('/')[-1]
                if isinstance(entry, dict) and leaf_key in entry:
                    return entry[leaf_key]
                else:
                    raise KeyError(f"Leaf '{leaf_key}' not found in entry")
        
        # Default path resolution for container queries
        result = self.model.findSIDR(self.data, sid=target_sid, keys=keys)
        
        if result is None:
            raise KeyError(f"Path not found or keys don't match: {xpath}")
        
        # Unwrap the {sid: value} dict
        value = result[target_sid]
        
        if '/' in target_path:
            parent_path = '/'.join(target_path.split('/')[:-1]) + '/'
        else:
            parent_path = '/'
        
        # Make a deep copy before conversion to avoid modifying self.data
        value_copy = copy.deepcopy(value)
        
        # Create wrapped structure and convert
        wrapped = {target_sid: value_copy}
        self.model.lookupIdentifierWithoutRecursion(wrapped, delta=0, path=parent_path)
        
        # Extract converted value
        node_identifier = target_path.split('/')[-1]
        return wrapped.get(node_identifier, wrapped.get(target_sid, value_copy))
    
    def __setitem__(self, xpath, value):
        """
        Set value at XPath.
        Example: db["/measurements/measurement[type='solar-radiation'][id='0']/value"] = 42
                 db["/measurements/measurement[type='solar-radiation'][id='0']"] = {...YANG dict...}
        
        Can also create new list entries automatically:
        Ex: db["/measurements/measurement[type='solar-radiation'][id='1']/precision"] = 3
            - Creates the list entry if needed
        """
        import copy
        import json
        
        segments = self._parse_xpath(xpath)
        
        try:
            target_sid, keys = self._resolve_path(xpath)
        except KeyError:
            # Path resolution failed - will be handled below if creation is needed
            target_sid = None
            keys = None
        
        target_path = self.model.ids.get(target_sid, '')
        
        # If value is a dict/list, convert from YANG to CBOR format first
        if isinstance(value, (dict, list)):
            value_copy = copy.deepcopy(value)
            
            wrapper = {}
            current = wrapper
            path_parts = [p for p in target_path.strip('/').split('/') if p]
            
            for part in path_parts[:-1]:
                current[part] = {}
                current = current[part]
            current[path_parts[-1]] = value_copy
            
            cbor_data = self.model.toCORECONF(json.dumps(wrapper))
            cbor_dict = cbor.loads(cbor_data)
            
            current = cbor_dict
            for part in path_parts[:-1]:
                part_path = '/' + '/'.join(path_parts[:path_parts.index(part)+1])
                if part_path in self.model.sids:
                    part_sid = self.model.sids[part_path]
                    parent_sid = self.model.sids.get('/' + '/'.join(path_parts[:path_parts.index(part)]))
                    if parent_sid:
                        delta_key = part_sid - parent_sid
                        current = current[delta_key]
                    else:
                        current = current[part_sid]
            
            final_path = '/' + '/'.join(path_parts)
            final_sid = self.model.sids[final_path]
            parent_sid = self.model.sids.get('/' + '/'.join(path_parts[:-1]))
            if parent_sid:
                delta_key = final_sid - parent_sid
                cbor_value = current[delta_key]
            else:
                cbor_value = current[final_sid]
        else:
            cbor_value = value
        
        result = self.model.findSIDR(self.data, sid=target_sid, keys=keys, value=cbor_value)
        
        if result is None:
            # Materialize missing path parts in JSON (containers + list entries).
            # This allows creation from an empty DB and nested list predicates.
            current_json = json.loads(self.to_json())
            qualified_parts = [p for p in target_path.strip('/').split('/') if p] if target_path else []

            def _to_typed_predicates(predicates):
                typed = {}
                for key_name, key_value in predicates.items():
                    try:
                        typed[key_name] = int(key_value)
                    except ValueError:
                        typed[key_name] = key_value
                return typed

            def _match_dict_key(node, short_name, preferred_name):
                if short_name in node:
                    return short_name
                if preferred_name in node:
                    return preferred_name
                for existing_key in node.keys():
                    if isinstance(existing_key, str) and existing_key.endswith(":" + short_name):
                        return existing_key
                return None

            nav = current_json
            for idx, (seg_name, seg_preds) in enumerate(segments):
                is_last = idx == len(segments) - 1
                preferred_name = qualified_parts[idx] if idx < len(qualified_parts) else seg_name

                if seg_preds:
                    if not isinstance(nav, dict):
                        raise KeyError(f"Path not found or keys don't match: {xpath}")

                    list_key = _match_dict_key(nav, seg_name, preferred_name)
                    if list_key is None:
                        nav[preferred_name] = []
                        list_key = preferred_name

                    if not isinstance(nav[list_key], list):
                        raise KeyError(f"Path not found or keys don't match: {xpath}")

                    typed_preds = _to_typed_predicates(seg_preds)
                    target_entry = None
                    for entry in nav[list_key]:
                        if isinstance(entry, dict) and all(entry.get(k) == v for k, v in typed_preds.items()):
                            target_entry = entry
                            break

                    if target_entry is None:
                        target_entry = dict(typed_preds)
                        nav[list_key].append(target_entry)

                    if is_last:
                        if isinstance(value, dict):
                            target_entry.update(value)
                    nav = target_entry
                    continue

                if not isinstance(nav, dict):
                    raise KeyError(f"Path not found or keys don't match: {xpath}")

                child_key = _match_dict_key(nav, seg_name, preferred_name)
                if is_last:
                    final_key = child_key if child_key is not None else preferred_name
                    nav[final_key] = value if not isinstance(value, (dict, list)) else copy.deepcopy(value)
                else:
                    if child_key is None:
                        nav[preferred_name] = {}
                        child_key = preferred_name
                    elif not isinstance(nav[child_key], dict):
                        raise KeyError(f"Path not found or keys don't match: {xpath}")
                    nav = nav[child_key]

            json_str = json.dumps(current_json)
            cbor_data = self.model.toCORECONF(json_str)
            self.data = cbor.loads(cbor_data)
            return
    
    def to_cbor(self):
        """Export modified data back to CBOR."""
        return cbor.dumps(self.data)
    
    def to_json(self):
        """Export data as JSON string."""
        return self.model.toJSON(self.to_cbor())

    def __str__(self):
        """Return a human-friendly JSON representation for print(db)."""
        try:
            return json.dumps(json.loads(self.to_json()), indent=2)
        except Exception:
            return self.to_json()

    def __repr__(self):
        """Keep interactive output consistent with print(db)."""
        return self.__str__()
    
    def __delitem__(self, xpath):
        """
        Delete value at XPath.
        Example: del db["/measurements/measurement[type='solar-radiation'][id='1']"]
                 del db["/measurements/measurement[type='solar-radiation'][id='1']/precision"]
        """
        import json
        
        segments = self._parse_xpath(xpath)
        
        # Check if this is a list item deletion (has predicates)
        list_seg_idx = None
        for i in range(len(segments) - 1, -1, -1):
            if segments[i][1]:  # Has predicates - is a list item
                list_seg_idx = i
                break
        
        if list_seg_idx is None:
            raise KeyError(f"Can only delete list items or their leaves: {xpath}")
        
        # Get the list item segment
        list_item_name, list_item_preds = segments[list_seg_idx]
        list_container_parts = [s[0] for s in segments[:list_seg_idx]]
        
        # Export current JSON
        current_json = json.loads(self.to_json())
        
        # Navigate to the list container
        nav = current_json
        for part in list_container_parts:
            if part in nav:
                nav = nav[part]
            else:
                found = False
                for key in nav.keys():
                    if key.endswith(":" + part):
                        nav = nav[key]
                        found = True
                        break
                if not found:
                    raise KeyError(f"Container {part} not found: {xpath}")
        
        # Get the list itself
        if list_item_name in nav:
            measurement_list = nav[list_item_name]
        else:
            found = False
            for key in nav.keys():
                if key.endswith(":" + list_item_name):
                    measurement_list = nav[key]
                    found = True
                    break
            if not found:
                raise KeyError(f"List {list_item_name} not found: {xpath}")
        
        if not isinstance(measurement_list, list):
            raise ValueError(f"Expected list at {list_item_name}")
        
        # If deleting a leaf within an entry, just remove that field
        if list_seg_idx < len(segments) - 1:
            # Find the entry matching the predicates and remove the leaf
            leaf_parts = [s[0] for s in segments[list_seg_idx+1:]]
            leaf_name = leaf_parts[-1]
            
            for entry in measurement_list:
                if isinstance(entry, dict) and all(
                    entry.get(k) == (int(v) if v.isdigit() else v)
                    for k, v in list_item_preds.items()
                ):
                    if leaf_name in entry:
                        del entry[leaf_name]
                    break
        else:
            # Delete the entire list entry
            # Find and remove the entry matching all predicates
            for i, entry in enumerate(measurement_list):
                if isinstance(entry, dict) and all(
                    entry.get(k) == (int(v) if v.isdigit() else v)
                    for k, v in list_item_preds.items()
                ):
                    del measurement_list[i]
                    break
        
        # Re-export and reload
        json_str = json.dumps(current_json)
        cbor_data = self.model.toCORECONF(json_str)
        self.data = cbor.loads(cbor_data)


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

    def findSIDR(self, obj, sid=None, keys=None, value=None, delta=0, path='/', depth=None, no_keys=False):
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
                            if no_keys and sid is not None and sid == p_sid:
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

    def loadDB(self, cbor_data = cbor.dumps({})):
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
