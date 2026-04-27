# CORECONF Conversion library

from .sid import ModelSID
from .datastore import CORECONFDatastore
import json
import base64
import cbor2 as cbor
import logging

_logger = logging.getLogger(__name__)


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
    """
    Main class for encoding/decoding CORECONF data against a YANG model.

    Args:
        sid_files: Path or list of paths to .sid files (generated with --sid-extension).
        model_description_file: Path to YANG model description JSON (required for validation).

    Example:
        - ccm = CORECONFModel(sid_files=["module-1.sid", "module-2.sid"])
        - ccm = CORECONFModel("module.sid", model_description_file="description.json")
    """

    def __init__(self, 
                 sid_files: list[str] | str, 
                 model_description_file: str = None):
        
        self.model_description_file = model_description_file
        self.yang_ietf_modules_paths = ["."]
        # Handle both single string and list of strings
        if isinstance(sid_files, str):
            sid_files = [sid_files]
        super().__init__(sid_files)

    def add_modules_path(self, path: str | list[str]) -> None:
        """
        Add a path or list of paths to YANG module dependencies.

        Args:
            path: Path string or list of paths to YANG IETF modules directory.

        Example:
            - model.add_modules_path("./yang_modules")
            - model.add_modules_path(["./modules", "/usr/share/yang"])
        """

        if type(path) is str:
            self.yang_ietf_modules_paths.append(path)
        elif type(path) is list:
            self.yang_ietf_modules_paths.extend(path)
        else:
            raise TypeError("Can only add path string or list of paths.")

    def _load_json_input(self, json_input):
        """Handle JSON string or file path input."""

        if json_input.strip().endswith(".json"):
            _logger.debug("Handling JSON input '%s' as a file path", json_input)
            with open(json_input, 'r') as f:
                return json.load(f)
        else:
            _logger.debug("Handling JSON input as content (length=%d)", len(json_input))
            return json.loads(json_input)

    def _convert_leaf_value(self, leaf, dtype, to_cbor, use_native_types=True):
        """
        Convert a leaf value between model (Python/JSON) and CBOR representations
        according to its YANG data type.

        Args:
            leaf: The input leaf value.
            dtype: The YANG data type definition for the value.
            to_cbor (bool): If True, convert from model representation to CBOR-compatible
                form. If False, convert from CBOR to model representation.
            use_native_types (bool): If False during decoding, preserve JSON-compatible
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
            # Decoding (i.e. not to_cbor):
            if leaf.tag == BITS_CBOR_TAG_VALUE:
                return str(leaf.value)
            if leaf.tag == ENUMERATION_CBOR_TAG_VALUE:
                return dtype[str(leaf.value)]
            if leaf.tag == IDENTITYREF_CBOR_TAG_VALUE:
                return self.ids[leaf.value]
            if leaf.tag == INSTANCE_IDENTIFIER_CBOR_TAG_VALUE:
                _logger.debug("Decoding CBOR tag %d value (%d) without handling", leaf.tag, leaf.value)
                return leaf.value # ?
            if leaf.tag == SID_CBOR_TAG_VALUE:
                _logger.debug("Decoding CBOR tag %d value (%d) without handling", leaf.tag, leaf.value)
                return leaf.value # ?
            else:
                _logger.warning("Unexpected CBOR tag %d during decoding; returning value as-is.", leaf.tag)
                return leaf.value

        elif type(dtype) is str:
            if dtype == "string":
                return str(leaf)
            elif dtype in ["int8", "int16", "int32", "int64",
                            "uint8", "uint16", "uint32", "uint64"]:
                # RFC 7951: int64/uint64 must be strings in JSON to avoid precision loss,
                # but CBOR uses native integers. Smaller types are safe as JSON numbers.
                if not to_cbor and dtype in ["int64", "uint64"] and not use_native_types:
                    return str(leaf)
                else:
                    return int(leaf)
            elif dtype == "decimal64":
                # RFC 7951: decimal64 must be a string in JSON to avoid precision loss,
                # but CBOR can use a float or string representation
                if not to_cbor and not use_native_types:
                    return str(leaf)
                else:
                    return float(leaf)
            elif dtype == "binary":
                if to_cbor:
                    dec = base64.b64decode(leaf)
                    return dec
                else:
                    enc = base64.b64encode(leaf)
                    return enc.decode()
            elif dtype == "boolean":
                # ret = True if obj == "true" else False
                _logger.debug("Handling boolean type as bool(leaf)")
                return bool(leaf)
            elif dtype == "inet:uri":
                return str(leaf)
            elif dtype == "identityref": # sid <-> 'module:identity'
                return self.sids[leaf] if to_cbor else self.ids[leaf]
            elif dtype in ["empty", "leafref", "instance-identifier", "bits"]: # just return obj
                _logger.warning("Data type %s not yet handled; returning value as-is.", dtype)
                return leaf

        elif type(dtype) is dict: # enumeration ({"value":"name"})
            if to_cbor: # inverse dict, w value as int
                dtype = {v: int(k) for k, v in dtype.items()}
            return dtype[str(leaf)]

        elif type(dtype) is list: # union
            _logger.debug("Resolving union type (to_cbor=%s, value=%r, candidates=%s)", to_cbor, leaf, dtype)
            for sub_dtype in dtype:
                try:
                    val = self._convert_leaf_value(leaf, sub_dtype, to_cbor, use_native_types)
                    _logger.debug("Matched union subtype %s", sub_dtype)

                    # Special cases - RFC 9254 Section 6.12
                    if to_cbor:
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

            _logger.warning("No matching subtype found for union %s (value=%s); returning value as-is.", dtype, leaf)
            return leaf # fallback

        # RFC 7951: Fallback for Decimal objects (e.g., from unrecognized typedefs)
        # Decimal values must be strings in JSON to maintain precision
        if not to_cbor and not use_native_types:
            from decimal import Decimal
            if isinstance(leaf, Decimal):
                _logger.debug("Converting Decimal to string for JSON compatibility (value=%r)", leaf)
                return str(leaf)

        _logger.warning("Unrecognized type: %s; returning value as-is.", dtype)
        return leaf # fallback

    def _identifier_to_sid_tree_recursive(self, obj, path="/", parent_sid=0):
        """
        Convert an identifier-keyed tree into a SID-keyed tree (recursive).

        Args:
            obj: Current identifier-based tree.
            path: Current identifier path.
            parent_sid: Parent SID value.

        Returns:
            SID-keyed tree.
        """

        if type(obj) is dict:
            sid_tree = {}
            for k, v in obj.items():
                node_path = path + k       # get full identifier path
                key = self.sids[node_path] # look for SID value

                value = self._identifier_to_sid_tree_recursive(v, node_path+"/", key)  # dive in

                sid_tree[key - parent_sid] = value
            return sid_tree

        elif type(obj) is list:
            sid_tree_list = []
            for e in obj:   # get each element of the list
                value = self._identifier_to_sid_tree_recursive(e, path, parent_sid)  # dive in
                sid_tree_list.append(value)
            return sid_tree_list

        # Leaves:
        else:
            # get leaf data type according to model
            # and cast to correct data type.
            dtype = self.types[path[:-1]]
            return self._convert_leaf_value(obj, dtype, to_cbor=True)
            
    def _identifier_to_sid_tree(self, obj, path='/', parent_sid=0):
        """
        Convert an identifier-keyed tree into a SID-keyed tree (iterative).

        Args:
            obj: Current identifier-based tree.
            path: Current identifier path.
            parent_sid: Parent SID value.

        Returns:
            SID-keyed tree.
        """

        _logger.debug("Using iterative identifier-tree to SID-tree conversion")

        stack = [(_ValueWrapper(obj), path, parent_sid)]

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
                current_object.value = self._convert_leaf_value(current_object.value, dtype, to_cbor=True)
        
        # Unwrap the ValueClass objects before returning
        return(_unwrap_values(obj))

    def encode(self, config: dict) -> bytes:
        """
        Encode a Python dictionary config to CORECONF (CBOR).

        Args:
            config: Python dictionary with YANG identifier keys (e.g., "/example:greeting/message").

        Returns:
            CBOR-encoded bytes representing the CORECONF data.

        Example:
            - cbor_data = ccm.encode({"example:greeting/message": "Hello!"})
        """

        _logger.debug("Encoding config (keys=%d)", len(config))

        # "deepcopy" to not modify the input
        config_cpy = json.loads(json.dumps(config))

        # Transform to CORECONF
        sid_tree = self._identifier_to_sid_tree(config_cpy)
        cbor_data = cbor.dumps(sid_tree)

        _logger.debug("Encoding complete (bytes=%d)", len(cbor_data))

        return cbor_data
    
    def encode_json(self, json_config: str) -> bytes:
        """
        Encode a JSON string or file to CORECONF (CBOR).

        Args:
            json_config: JSON string or path to a .json file.

        Returns:
            CBOR-encoded bytes representing the CORECONF data.

        Example:
            - cbor_data = ccm.encode_json('{"example:greeting/message":"Hello!"}')
        """

        config = self._load_json_input(json_config)

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

    def _sid_to_identifier_tree_recursive(self, obj, sid_delta=0, path="/", use_native_types=True):
        """
        Convert a SID-keyed tree into an identifier-keyed tree (recursive).

        Args:
            obj: Current SID-based tree.
            sid_delta: SID offset from parent.
            path: Current identifier path.
            use_native_types: If True, use native Python types for leaf value conversion;
                if False, use JSON-encoding of YANG data representation.

        Returns:
            Identifier-keyed tree.
        """

        if type(obj) is dict:
            identifier_tree = {}
            for k, v in obj.items():
                sid = k + sid_delta        # get full SID value
                identifier = self.ids[sid] # look for identifier name

                value = self._sid_to_identifier_tree_recursive(v, sid, identifier, use_native_types)    # dive in

                identifier_key = identifier[len(path):].lstrip("/")
                identifier_tree[identifier_key] = value
            return identifier_tree

        elif type(obj) is list:
            identifier_tree_list = []
            for e in obj:   # get each element of the list
                value = self._sid_to_identifier_tree_recursive(e, sid_delta, path, use_native_types)    # dive in
                identifier_tree_list.append(value)
            return identifier_tree_list

        # Leaves:
        else:
            # get leaf data type according to model
            # and cast to correct data type.
            dtype = self.types[path]
            return self._convert_leaf_value(obj, dtype, to_cbor=False, use_native_types=use_native_types)

    def _sid_to_identifier_tree(self, obj, sid_delta=0, path='/', use_native_types=True):
        """
        Convert a SID-keyed tree into an identifier-keyed tree (iterative).

        Args:
            obj: Current SID-based tree.
            sid_delta: SID offset from parent.
            path: Current identifier path.
            use_native_types: If True, use native Python types for leaf value conversion;
                if False, use JSON-encoding of YANG data representation.

        Returns:
            Identifier-keyed tree.
        """

        _logger.debug("Using iterative SID-tree to identifier-tree conversion")

        stack = [(_ValueWrapper(obj), sid_delta, path)]

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
                current_object.value = self._convert_leaf_value(current_object.value, dtype, to_cbor=False, use_native_types=use_native_types)

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

        _logger.debug(
            "Executing SID query (sid=%s, keys=%s, update=%s, depth=%s)",
            sid, keys, value is not None, depth
        )

        result = _walk(obj, delta, path, keys)

        if result is None:
            _logger.debug("SID query returned no result (sid=%s, keys=%s)", sid, keys)

        return result

    def decode(self, data: bytes, as_rfc7951: bool = False) -> dict:
        """
        Decode CORECONF (CBOR) data to a Python dictionary.

        Args:
            data: CBOR-encoded bytes.
            as_rfc7951: If False (default), returns Python native types (int, float, bool).
                        If True, returns RFC 7951-compliant types (e.g., int64 as string).

        Returns:
            Python dictionary with YANG identifier keys.

        Example:
            - cfg = ccm.decode(cbor_data)                   # native types
            - cfg = ccm.decode(cbor_data, as_rfc7951=True)  # RFC 7951-compliant
        """

        _logger.debug("Decoding CBOR data (bytes=%d)", len(data))

        data = cbor.loads(data)
        config = self._sid_to_identifier_tree(data, use_native_types=(not as_rfc7951))

        _logger.debug("Decoding complete (as_rfc7951=%s, keys=%d)", as_rfc7951, len(config))

        return config

    def decode_to_json(self, data: bytes) -> str:
        """
        Decode CORECONF (CBOR) data to a JSON string (RFC 7951-compliant).

        Args:
            data: CBOR-encoded bytes.

        Returns:
            JSON string with RFC 7951-compliant data types.

        Example:
            - json_str = ccm.decode_to_json(cbor_data)
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
        pyd = self._sid_to_identifier_tree(data, use_native_types=return_pydict)

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
        Validate a JSON config string or file against the YANG data model.

        Args:
            json_config: JSON string or path to file to validate.

        Raises:
            RuntimeError: If model_description_file is not set.
            ImportError: If yangson package is not installed.
            ConfigValidationError: If validation fails.

        Example:
            - ccm.validate_json('{"example:greeting/message":"Hello!"}')
        """

        if self.model_description_file is None:
            raise RuntimeError("Model not configured for validation: missing model_description_file.")

        try:
            from yangson import DataModel
        except ImportError:
            raise ImportError("Validation requires 'yangson' package.")

        config = self._load_json_input(json_config)

        dm = DataModel.from_file(
            self.model_description_file,
            self.yang_ietf_modules_paths
        )
        data = dm.from_raw(config)

        try:
            data.validate()
            _logger.info("Config validation passed")
        except Exception as e:
            # Add context and preserve the original exception chain
            raise ConfigValidationError(f"Config validation failed: {e}") from e

    def _validate_config(self, config):
        """
        Validate Python dictionary config against the model.
        Raises on validation error. No-op if validation is not configured.
        > DEPRECATED: Use validate_json().
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

    def create_datastore(self, data: dict = None):
        """
        Load an identifier-keyed dict into a high-level datastore interface.

        Args:
            data: Python dictionary with YANG identifier keys (e.g., {"example:greeting/message": "Hello!"})
                  If None, creates an empty datastore.

        Returns:
            CORECONFDatastore instance for easy navigation and modification

        Example:
            ds = model.create_datastore({"example:greeting/message": "Hello!"})
            value = ds["/measurements/measurement[type='solar-radiation'][id='0']/value"]
            ds["/measurements/measurement[type='solar-radiation'][id='0']/value"] = 42
        """

        if data is None:
            data = {}

        # "deepcopy" to not modify the input
        data_cpy = json.loads(json.dumps(data))

        sid_tree = self._identifier_to_sid_tree(data_cpy)

        return CORECONFDatastore(self, sid_tree)

    def create_datastore_from_cbor(self, cbor_data: bytes):
        """
        Load CBOR data into a high-level datastore interface.

        Args:
            cbor_data: CBOR-encoded bytes (already in CORECONF/SID-keyed format)

        Returns:
            CORECONFDatastore instance for easy navigation and modification

        Example:
            ds = model.create_datastore_from_cbor(cbor_data)
            value = ds["/measurements/measurement[type='solar-radiation'][id='0']/value"]
        """

        sid_tree = cbor.loads(cbor_data)

        return CORECONFDatastore(self, sid_tree)

    def create_datastore_from_json(self, json_config: str):
        """
        Load JSON data into a high-level datastore interface.

        Args:
            json_config: JSON string or path to a .json file with YANG identifier keys.

        Returns:
            CORECONFDatastore instance for easy navigation and modification

        Example:
            ds = model.create_datastore_from_json('{"example:greeting/message":"Hello!"}')
            ds = model.create_datastore_from_json("config.json")
        """

        config = self._load_json_input(json_config)

        return self.create_datastore(config)
