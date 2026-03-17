import json
import cbor2 as cbor

try:
    from typing import TYPE_CHECKING
except Exception:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from .pycoreconf import CORECONFModel

class CORECONFDatabase:
    """
    High-level interface to navigate and modify CORECONF data using XPath-like paths.
    Usage: db["/measurements/measurement[type='solar-radiation'][id='0']/value"]
    """
    
    def __init__(self, model: "CORECONFModel", cbor_data: bytes = None):
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

    def _resolve_identity_to_sid(self, identity_value):
        """
        Resolve an identityref textual value to its SID.

        Accepted formats:
        - "module:identity"
        - "/module:identity"
        - "identity" (only when unique across loaded modules)
        """
        if not isinstance(identity_value, str):
            raise ValueError(f"Identity must be a string, got: {type(identity_value).__name__}")

        # Try exact key as-is.
        if identity_value in self.model.sids:
            return self.model.sids[identity_value]

        # Try with leading slash.
        prefixed = identity_value if identity_value.startswith("/") else "/" + identity_value
        if prefixed in self.model.sids:
            return self.model.sids[prefixed]

        # If unqualified identity name is provided, resolve only when unambiguous.
        normalized = identity_value.lstrip("/")
        if ":" not in normalized:
            matches = []
            for candidate_path, candidate_sid in self.model.sids.items():
                if not isinstance(candidate_path, str):
                    continue
                candidate = candidate_path.lstrip("/")

                # Only consider top-level qualified names, e.g. module:identity.
                if "/" in candidate or ":" not in candidate:
                    continue

                candidate_short = candidate.split(":", 1)[1]
                if candidate_short == normalized:
                    matches.append(candidate_sid)

            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ValueError(f"Ambiguous identity name: {identity_value}")

        raise ValueError(f"Identity not found in model: {identity_value}")

    def _format_identity_for_xpath(self, raw_value):
        """
        Format identityref value for XPath predicates.

        Prefer short identity names (without module prefix) when they are
        unambiguous in the loaded model(s). Otherwise keep module-qualified form.
        """
        full_identity = self.model.ids.get(raw_value, raw_value)
        if not isinstance(full_identity, str):
            return full_identity

        full_identity = full_identity.lstrip("/")
        if ":" not in full_identity:
            return full_identity

        short_identity = full_identity.split(":", 1)[1]

        try:
            resolved_from_short = self._resolve_identity_to_sid(short_identity)
            if resolved_from_short == raw_value:
                return short_identity
        except ValueError:
            pass

        return full_identity

    def _resolve_enum_to_int(self, enum_type, enum_value):
        """
        Resolve enum predicate value to its integer representation.

        Accepted formats:
        - enum name (e.g. "delta")
        - enum integer as string (e.g. "1")
        - enum integer (e.g. 1)
        """
        if isinstance(enum_value, int):
            if str(enum_value) in enum_type:
                return enum_value
            raise ValueError(f"Enum value out of range: {enum_value}")

        if not isinstance(enum_value, str):
            raise ValueError(f"Enum value must be str or int, got: {type(enum_value).__name__}")

        if enum_value in enum_type:
            return int(enum_value)

        matches = [int(k) for k, v in enum_type.items() if v == enum_value]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous enum name: {enum_value}")

        try:
            as_int = int(enum_value)
            if str(as_int) in enum_type:
                return as_int
        except ValueError:
            pass

        raise ValueError(f"Enum value not found: {enum_value}")

    def _format_enum_for_xpath(self, raw_value, enum_type):
        """
        Format enum key value for XPath predicates.

        Converts integer enum values to their symbolic names when available.
        """
        key = str(raw_value)
        if key in enum_type:
            return enum_type[key]
        return raw_value
    
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
                                # Convert identity name to SID.
                                # Unqualified values are accepted when unambiguous.
                                key_value = self._resolve_identity_to_sid(key_value)
                        elif isinstance(dtype, dict):
                            # Enumeration key: accept symbolic names and numeric forms.
                            key_value = self._resolve_enum_to_int(dtype, key_value)
                    
                    key_values.append(key_value)
        
        target_sid = self.model.sids[yang_path]
        return target_sid, key_values
    
    def __getitem__(self, xpath):
        """
        Get value at XPath.
        Example: db["/measurements/measurement[type='solar-radiation'][id='0']/value"]
        Returns values with YANG identifiers instead of SIDs, or None if not found.
        """
        import copy

        # Resolve the path — return None if the path does not exist in the model
        try:
            target_sid, keys = self._resolve_path(xpath)
        except (KeyError, ValueError):
            return None
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
                    return None

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
                    return None
        
        # Default path resolution for container queries
        result = self.model.findSIDR(self.data, sid=target_sid, keys=keys)
        
        if result is None:
            return None  # when used in test, this allows checking for non-existence without raising an exception

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
        
    def get_keys(self, xpath):
        """
        Return list-key predicates for entries under a list XPath.

        Example:
            db.get_keys("/measurements/measurement")
            -> ["[type='module:identity'][id='0']", ...]

        If XPath includes predicates, returns the corresponding predicate string
        as a single-item list.
        """
        try:
            target_sid, keys = self._resolve_path(xpath)
        except (KeyError, ValueError):
            return None

        key_sids = self.model.key_mapping.get(str(target_sid))
        if not key_sids:
            return None

        def _format_predicates_from_values(values):
            parts = []
            for key_sid, raw_value in zip(key_sids, values):
                key_path = self.model.ids.get(key_sid, f"unknown_key_{key_sid}")
                key_leaf_name = key_path.split("/")[-1].split(":")[-1]
                key_dtype = self.model.types.get(key_path)

                key_value = raw_value
                if key_dtype == "identityref":
                    key_value = self._format_identity_for_xpath(raw_value)
                elif isinstance(key_dtype, dict): # enum
                    key_value = self._format_enum_for_xpath(raw_value, key_dtype)

                parts.append(f"[{key_leaf_name}='{key_value}']")
            return "".join(parts)

        # Predicates already present in the XPath: return a single canonical filter.
        if keys:
            return [_format_predicates_from_values(keys)]

        child = self.model.findSIDR(self.data, sid=target_sid, keys=[], no_keys=True)
        if child is None:
            return []

        entries = child.get(target_sid, [])
        if not isinstance(entries, list):
            return []

        answer = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            values = []
            complete = True
            for key_sid in key_sids:
                key_delta = key_sid - target_sid
                if key_delta not in entry:
                    complete = False
                    break
                values.append(entry[key_delta])

            if complete:
                answer.append(_format_predicates_from_values(values))

        return answer
    
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
