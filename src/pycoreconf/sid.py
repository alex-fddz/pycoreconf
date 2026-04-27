import json
import warnings
import logging

_logger = logging.getLogger(__name__)

class ModelSID:
    """
    Base class for loading and indexing YANG model SID files.

    Holds the SID mapping tables required for CORECONF conversion.

    Attributes:
        sid_files: List of paths to .sid files.
        sids: Mapping of YANG identifier to SID value.
        types: Mapping of YANG identifier to data type.
        ids: Inverse mapping of SID value to identifier.
        key_mapping: Mapping of list SIDs to their key component SIDs.

    Example:
        - model = ModelSID(["module-1.sid", "module-2.sid"])
    """

    def __init__(self, sid_files: list[str]):
        self.sid_files = sid_files # .sid file paths
        self.sids, self.types, self.key_mapping = self._collect_sid_data() #req. ltn22/pyang
        self.ids = {v: k for k, v in self.sids.items()} # {sid:id}

    def _parse_sid_file(self, sid_filename: str) -> tuple:
        """
        Parse a single SID file.

        Args:
            sid_filename: Path to the .sid file.

        Returns:
            Tuple of (module_name: str, items: list, key_mapping: dict).

        Raises:
            FileNotFoundError: If the SID file does not exist.
            JSONDecodeError: If the file is not valid JSON.
        """

        with open(sid_filename, "r") as f:
            obj = json.load(f)

        if len(obj) == 1 and list(obj.keys())[0].endswith("sid-file"):
            sid_data = list(obj.values())[0]  # RFC‑9595 standard container
        else:
            warnings.warn(
                f"Legacy or non-standard SID file detected ({sid_filename}). "
                "Regenerate it using the latest ltn22/pyang.",
                stacklevel=2
            )
            sid_data = obj

        items = sid_data.get("item") or sid_data.get("items", [])
        module_name = sid_data.get("module-name", "unknown")
        key_mapping = sid_data.get("key-mapping", None)

        if key_mapping is None:
            key_mapping = {}
            warnings.warn(
                f"{sid_filename} does not contain SID extensions. "
                "Regenerate it using ltn22/pyang with the --sid-extension option.",
                stacklevel=2
            )

        return module_name, items, key_mapping

    def _collect_sid_data(self) -> tuple:
        """
        Aggregate SID mappings from all loaded SID files.

        Builds the following tables:
            - sids: {identifier: sid_value} for all data nodes
            - types: {identifier: yang_type} for typed nodes
            - key_mapping: {list_sid: [key_sid, ...]} for list key resolution

        Returns:
            Tuple of (sids: dict, types: dict, key_mapping: dict).
        """

        # Initialize mapping tables
        sids = {}
        types = {}
        key_mapping = {}

        for sid_filename in self.sid_files:
            
            # Read the contents of the sid files
            _logger.debug("Loading SID file: %s", sid_filename)
            module_name, items, km = self._parse_sid_file(sid_filename)

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    sids[f'{module_name}:{item["identifier"]}'] = int(item["sid"])

                else:
                    sids[item["identifier"]] = int(item["sid"])

                if "type" in item.keys():
                    types[item["identifier"]] = item["type"]

                key_mapping.update(km)

            # Save module name & ranges = {'module-name': [(start, end)], ...} ?
            # ranges[obj["module-name"]] = _parse_assignment_ranges(obj)

            _logger.debug(
                "Parsed SID module '%s': items=%d, typed-leaves=%d, key-mappings=%d",
                module_name, len(items), len(types), len(km)
            )

        _logger.info(
            "Collected SID data: %d module(s), %d sids, %d typed leaves, %d key mappings",
            len(self.sid_files), len(sids), len(types), len(key_mapping)
        )
            
        return sids, types, key_mapping
