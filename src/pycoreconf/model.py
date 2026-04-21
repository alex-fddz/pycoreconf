# CORECONF Conversion library

from .sid import ModelSID
from .datastore import CORECONFDatastore
import json
import base64
import cbor2 as cbor


class ConfigValidationError(Exception):
    """Raised when config validation fails; wraps the original exception."""
    pass


class _ValueWrapper:
    """Wrapper class to encapsulate objects through the SID tree iteration."""

    def __init__(self, value):
        self.value = value

def _unwrap_values(obj):
    """Unwrap ValueWrapper objects after iterative SID tree transformation."""

    internal_stack = [obj]

    while internal_stack:
        current_object = internal_stack.pop()

        if type(current_object) == dict:
            keys = list(current_object.keys())
            for key in keys:
                current_object[key] = current_object[key].value
                internal_stack.append(current_object[key])
        
        elif type(current_object) == list:
            for i in range(len(current_object)):
                current_object[i] = current_object[i].value
                internal_stack.append(current_object[i])

    return obj


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
        Required for configuration data validation.
        """

        if type(path) is str:
            self.yang_ietf_modules_paths.append(path)
        elif type(path) is list:
            self.yang_ietf_modules_paths.extend(path)
        else:
            raise TypeError("Can only add path string or list of paths.")

    def _convert_leaf_value(self, leaf, dtype, encoding, native_types=True):
        """
        Convert a leaf value between model (Python/JSON) and CBOR representations
        according to its YANG data type.

        Args:
            leaf: The input leaf value.
            dtype: The YANG data type definition for the value.
            encoding (bool): If True, convert from model representation to CBOR-compatible
                form. If False, convert from CBOR to model representation.
            native_types (bool): If False during decoding, preserve JSON-compatible
                representations (e.g. int64/decimal64 as strings).

        Returns:
            The converted value.
        """

        # XXX: Refactor and/or split (encoding/decoding) this function.

        BITS_CBOR_TAG_VALUE = 43
        ENUMERATION_CBOR_TAG_VALUE = 44
        IDENTITYREF_CBOR_TAG_VALUE = 45
        INSTANCE_IDENTIFIER_CBOR_TAG_VALUE = 46
        SID_CBOR_TAG_VALUE =  47

        if isinstance(leaf, cbor.CBORTag):
            # Decoding:
            if leaf.tag == BITS_CBOR_TAG_VALUE:
                return str(leaf.value)
            if leaf.tag == ENUMERATION_CBOR_TAG_VALUE:
                return dtype[str(leaf.value)]
            if leaf.tag == IDENTITYREF_CBOR_TAG_VALUE:
                return self.ids[leaf.value]
            if leaf.tag == INSTANCE_IDENTIFIER_CBOR_TAG_VALUE:
                return leaf.value # ?
            if leaf.tag == SID_CBOR_TAG_VALUE:
                return leaf.value # ?
            else:
                print(f"[X] Unexpected CBOR Tag {leaf.tag}.")

        elif type(dtype) is str:
            if dtype == "string":
                return str(leaf)
            elif dtype in ["int8", "int16", "int32", "int64",
                            "uint8", "uint16", "uint32", "uint64"]:
                # RFC 7951: int64/uint64 must be strings in JSON to avoid precision loss,
                # but CBOR uses native integers. Smaller types are safe as JSON numbers.
                if not encoding and dtype in ["int64", "uint64"] and not native_types:
                    return str(leaf)
                else:
                    return int(leaf)
            elif dtype == "decimal64":
                # RFC 7951: decimal64 must be a string in JSON to avoid precision loss,
                # but CBOR can use a float or string representation
                if not encoding and not native_types:
                    return str(leaf)
                else:
                    return float(leaf)
            elif dtype == "binary":
                if encoding:
                    dec = base64.b64decode(leaf)
                    return dec
                else:
                    enc = base64.b64encode(leaf)
                    return enc.decode()
            elif dtype == "boolean":
                # ret = True if obj == "true" else False
                return bool(leaf)
            elif dtype == "inet:uri":
                return str(leaf)
            elif dtype == "identityref": # sid <-> 'module:identity'
                return self.sids[leaf] if encoding else self.ids[leaf]
            elif dtype in ["empty", "leafref", "instance-identifier", "bits"]: # just return obj
                print(f"[-] Data type {dtype} found: Returning as is." )
                return leaf
            else:
                print("[X] Unrecognized obj type:", dtype, ". Returning as is.")

        elif type(dtype) is dict: # enumeration ({"value":"name"})
            if encoding: # inverse dict, w value as int
                dtype = {v: int(k) for k, v in dtype.items()}
            return dtype[str(leaf)]

        elif type(dtype) is list: # union
            # print(f"[-] Union: Finding subtype.. | {'encoding' if encoding else 'decoding'} | {dtype} | {obj}")
            for sub_dtype in dtype:
                try:
                    # print("  > trying subtype", sub_dtype)
                    val = self._convert_leaf_value(leaf, sub_dtype, encoding, native_types)
                    # print("  > OK")

                    # Special cases - RFC 9254 Section 6.12
                    if encoding:
                        if sub_dtype == "identityref":
                            return cbor.CBORTag(IDENTITYREF_CBOR_TAG_VALUE, val)
                        elif sub_dtype == "bits":
                            return cbor.CBORTag(BITS_CBOR_TAG_VALUE, val)
                        elif sub_dtype == "instance-identifier":
                            return cbor.CBORTag(INSTANCE_IDENTIFIER_CBOR_TAG_VALUE, val)
                        elif isinstance(sub_dtype, dict): # enumeration
                            return cbor.CBORTag(ENUMERATION_CBOR_TAG_VALUE, val)

                    return val

                except Exception:
                    continue

            return leaf # fallback

        # RFC 7951: Fallback for Decimal objects (e.g., from unrecognized typedefs)
        # Decimal values must be strings in JSON to maintain precision
        if not encoding and not native_types:
            from decimal import Decimal
            if isinstance(leaf, Decimal):
                return str(leaf)

        return leaf # fallback

    def _identifier_to_sid_tree_recursive(self, obj, path="/", parent=0):
        """
        Convert an identifier-keyed tree into a SID-keyed tree (recursive).

        Args:
            obj: Current identifier-based tree.
            path: Current identifier path.
            parent: Parent SID.

        Returns:
            SID-keyed tree.
        """

        if type(obj) is dict:
            json_dict = {}
            for k, v in obj.items():
                element = path + k      # get full identifier path
                key = self.sids[element]     # look for SID value

                value = self._identifier_to_sid_tree_recursive(v, element+"/", key)  # dive in

                json_dict[key-parent] = value
            return json_dict

        elif type(obj) is list:
            json_list = []
            for e in obj:   # get each element of the list
                value = self._identifier_to_sid_tree_recursive(e, path, parent)  # dive in
                json_list.append(value)
            return json_list

        # Leaves:
        else:
            # get leaf data type according to model
            # and cast to correct data type.
            dtype = self.types[path[:-1]]
            return self._convert_leaf_value(obj, dtype, encoding=True)
            
    def _identifier_to_sid_tree(self, obj, path='/', parent=0):
        """
        Convert an identifier-keyed tree into a SID-keyed tree (iterative).

        Args:
            obj: Current identifier-based tree.
            path: Current identifier path.
            parent: Parent SID.

        Returns:
            SID-keyed tree.
        """

        stack = [(_ValueWrapper(obj), path, parent)]

        while stack:
            current_object, current_path, current_parent = stack.pop()
            current_value  = current_object.value

            # current_value is a dict here, iterate through key/value pairs and add values to the stack
            if type(current_value) == dict:
                keys = list(current_value.keys())

                for key in keys:
                    qualified_path = current_path + key
                    child_sid_value = self.sids[qualified_path]
                    sid_diff  = child_sid_value - current_parent
                    current_value[sid_diff] = _ValueWrapper(current_value.pop(key))
                    stack.append((current_value[sid_diff], qualified_path+"/", child_sid_value))
            
            # current_value is a list type, append each of the object in current_value to the stack
            elif type(current_value) == list:
                for i in range(len(current_value)):
                    current_value[i] = _ValueWrapper(current_value[i])
                    stack.append((current_value[i], current_path, current_parent))
            
            # current_value is a leaf here, transform their datatype
            else:
                dtype = self.types[current_path[:-1]]
                current_object.value = self._convert_leaf_value(current_object.value, dtype, encoding=True)
        
        # Unwrap the ValueClass objects before returning
        return(_unwrap_values(obj))

    def encode(self, config: dict) -> bytes:
        """
        Encode a Python dictionary config into CORECONF.
        """

        # "deepcopy" to not modify the input
        config_cpy = json.loads(json.dumps(config))

        # Transform to CORECONF
        cc = self._identifier_to_sid_tree(config_cpy)

        return cbor.dumps(cc)
    
    def encode_json(self, json_config: str) -> bytes:
        """
        Encode a JSON-formatted string or .json file into CORECONF.
        """

        json_config = json_config.strip()
        try:
            # Parse the JSON string
            config = json.loads(json_config)
        except ValueError:
            # Load the JSON file
            with open(json_config, 'r') as f:
                config = json.load(f)

        return self.encode(config)

    def toCORECONF(self, config):
        """
        Convert JSON data, file, or dict to CORECONF.
        > DEPRECATED: Use encode() or encode_json().
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
            self._validate_config(cfg_dict)
        except Exception as e:
            # Add context and preserve the original exception chain
            raise ConfigValidationError(f"Input config validation failed: {e}") from e

        # Transform to CORECONF/CBOR
        cc = self._identifier_to_sid_tree(cfg_dict)

        return cbor.dumps(cc)

    def _sid_to_identifier_tree_recursive(self, obj, delta=0, path="/", native_types=True):
        """
        Convert a SID-keyed tree into an identifier-keyed tree (recursive).

        Args:
            obj: Current SID-based tree.
            delta: SID offset from parent.
            path: Current identifier path.
            native_types: If True, use native Python types for leaf value conversion;
                if False, use JSON-encoding of YANG data representation.

        Returns:
            Identifier-keyed tree.
        """

        if type(obj) is dict:
            json_dict = {}
            for k, v in obj.items():
                sid = k + delta             # get full identifier path
                identifier = self.ids[sid]       # look for SID value

                value = self._sid_to_identifier_tree_recursive(v, sid, identifier, native_types)    # dive in

                json_key = identifier[len(path):].lstrip("/")
                json_dict[json_key] = value
            return json_dict

        elif type(obj) is list:
            json_list = []
            for e in obj:   # get each element of the list
                value = self._sid_to_identifier_tree_recursive(e, delta, path, native_types)    # dive in
                json_list.append(value)
            return json_list

        # Leaves:
        else:
            # get leaf data type according to model
            # and cast to correct data type.
            dtype = self.types[path]
            return self._convert_leaf_value(obj, dtype, encoding=False, native_types=native_types)

    def _sid_to_identifier_tree(self, obj, delta=0, path='/', native_types=True):
        """
        Convert a SID-keyed tree into an identifier-keyed tree (iterative).

        Args:
            obj: Current SID-based tree.
            delta: SID offset from parent.
            path: Current identifier path.
            native_types: If True, use native Python types for leaf value conversion;
                if False, use JSON-encoding of YANG data representation.

        Returns:
            Identifier-keyed tree.
        """

        stack = [(_ValueWrapper(obj), delta, path)]

        while stack:
            current_object, current_delta, current_path = stack.pop()
            current_value = current_object.value

            # current_value is a dict here, iterate through key/value pairs and add values to the stack
            if type(current_value) is dict:
                keys = list(current_value.keys())
                for key in keys:
                    # get full identifier path
                    
                    sid = key + current_delta
                    # look for the original identifiers
                    identifier = self.ids[sid]
                    node_identifier = identifier[len(current_path):].lstrip("/")
                    current_value[node_identifier] = _ValueWrapper(current_value.pop(key))
                    stack.append((current_value[node_identifier], sid, identifier))
        
            # current_value is a list type, append each of the object in currentValue to the stack
            elif type(current_value) is list:
                for i in range(len(current_value)):
                    current_value[i] = _ValueWrapper(current_value[i])
                    stack.append((current_value[i], current_delta, current_path))

            # current_value is a leaf here, transform their datatype before adding to the current_object
            else:
                dtype = self.types[current_path]
                current_object.value = self._convert_leaf_value(current_object.value, dtype, encoding=False, native_types=native_types)

        # Unwrap the ValueClass objects before returning
        return(_unwrap_values(obj))

    def _execute_sid_query(self, obj, sid=None, keys=None, value=None, delta=0, path='/', depth=None):
        """
        SID query engine used by datastore (lookup, update, subtree extraction).

        Args:
            obj: SID-keyed configuration tree.
            sid: Target SID.
            keys: List of key values for list resolution.
            value: If set, updates matched node.
            delta: SID traversal offset.
            path: Current path context.
            depth: Max subtree depth (None=full, 0=leaves only, n=levels below match).

        Returns:
            {sid: subtree/value} or None.
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

    def decode(self, data: bytes, as_rfc7951: bool = False) -> dict:
        """
        Convert CORECONF (CBOR) data to Python dictionary.
        as_rfc7951: If False, returns python native types,
            If True, returns RFC7951-compliant data types.
        """

        data = cbor.loads(data)
        config = self._sid_to_identifier_tree(data, native_types=(not as_rfc7951))

        # Return Python dict object
        return config

    def decode_to_json(self, data: bytes) -> str:
        """
        Convert CORECONF (CBOR) data to JSON-formatted string, following RFC 7951.
        """

        config = self.decode(data=data, as_rfc7951=True)

        # Return JSON-formatted string
        return json.dumps(config)

    def toJSON(self, cbor_data, return_pydict=False): 
        """
        Convert CORECONF (CBOR) data to JSON-formatted string (or Python dictionary with native types).
        > DEPRECATED: Use decode() or decode_to_json().
        """

        data = cbor.loads(cbor_data)
        pyd = self._sid_to_identifier_tree(data, native_types=return_pydict)

        # Attempt to validate the output config
        try:
            self._validate_config(pyd)
        except Exception as e:
            # Add context and preserve the original exception chain
            raise ConfigValidationError(f"Output config validation failed: {e}") from e

        # + Option to directly save as file ?
        
        # Return JSON obj / pyDict
        return pyd if return_pydict else json.dumps(pyd) 

    def validate_json(self, json_config: str) -> None:
        """
        Validate a JSON-string config against the data model (syntax, semantics).
        Raises on validation error or misconfiguration.
        """

        if self.model_description_file is None:
            raise RuntimeError("Model not configured for validation: missing model_description_file.")

        try:
            from yangson import DataModel
        except ImportError:
            raise ImportError("Validation requires 'yangson' package.")

        config = json.loads(json_config)

        dm = DataModel.from_file(
            self.model_description_file,
            self.yang_ietf_modules_paths
        )
        data = dm.from_raw(config)
        data.validate()

    def _validate_config(self, config):
        """
        Validate Python dictionary config against the model.
        Raises on validation error. No-op if validation is not configured.
        """

        if self.model_description_file is None:
            return  # no validation configured

        try:
            from yangson import DataModel
        except ImportError:
            raise ImportError("Validation requires 'yangson' package.")

        dm = DataModel.from_file(
            self.model_description_file,
            self.yang_ietf_modules_paths
        )
        data = dm.from_raw(config)
        data.validate()

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
