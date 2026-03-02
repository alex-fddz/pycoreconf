import json

class ModelSID:
    """
    Class to define methods for reading a YANG model SID file and hold values.
    """

    def __init__(self, *sid_files):
        self.sid_files: tuple = sid_files # .sid file paths
        self.sids, self.types = self.getSIDsAndTypes() #req. ltn22/pyang
        self.ids = {v: k for k, v in self.sids.items()} # {sid:id}
        self.key_mapping = self._set_key_mapping(sid_files)

    def _load_sid_data(self, sid_filename):
        """
        Internal helper: load a SID file and return a tuple of (module_name, list_of_items, key_mapping).
        """

        with open(sid_filename, "r") as f:
            obj = json.load(f)

        if len(obj) == 1 and list(obj.keys())[0].endswith("sid-file"):
            sid_data = list(obj.values())[0]  # RFC‑9595 standard container
        else:
            print(f"Warning: legacy/non-standard SID file loaded ({sid_filename}). Some features may not work properly.")
            sid_data = obj  # legacy/non-standard format

        items = sid_data.get("item") or sid_data.get("items", [])
        module_name = sid_data.get("module-name", "unknown")
        key_mapping = sid_data.get("key-mapping", None)

        return module_name, items, key_mapping

    def getSIDsAndTypes(self):
        """
        Read SID file and return { identifier : sid } + { identifier : type } dictionaries.
        """
        sids = {} # init
        types = {} # init

        for sid_filename in self.sid_files:
            
            # Read the contents of the sid files
            module_name, items, _ = self._load_sid_data(sid_filename)

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    sids[module_name +":"+ item["identifier"]] = item["sid"] # XXX: use formatted string for better readability.

                else:
                    sids[item["identifier"]] = item["sid"]

                if "type" in item.keys():
                    types[item["identifier"]] = item["type"]

            # Save module name & ranges = {'module-name': [(start, end)], ...} ?
            # ranges[obj["module-name"]] = _parse_assignment_ranges(obj)
            
        return sids, types


    def getIdentifiers(self):
        """
        Read SID file and return { sid : identifier } dictionary.
        """

        ids = {} # init

        for sid_filename in self.sid_files:

            # Read the contents of the sid files
            module_name, items, _ = self._load_sid_data(sid_filename)

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    ids[item["sid"]] = module_name +":"+ item["identifier"]

                else:
                    ids[item["sid"]] = item["identifier"]

        return ids

    def getSIDs(self):
        """
        Read SID file and return { identifier : sid } dictionary.
        """

        sids = {} # init

        for sid_filename in self.sid_files:

            # Read the contents of the sid files
            module_name, items = self._load_sid_data(sid_filename)

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    sids[module_name +":"+ item["identifier"]] = item["sid"]

                else:
                    sids[item["identifier"]] = item["sid"]

        return sids

    def _set_key_mapping(self, sid_files: tuple):

        key_mapping = {}

        for sid_filename in sid_files:
            with open(sid_filename, mode='r') as f:
                obj = json.load(f)

            try:
                km = obj['key-mapping']
                key_mapping.update(km)
            except KeyError:
                print(f"{sid_filename} has not been generated with the --sid-extension option.\n" \
                    + "Some conversion capabilities may not work. See http://github.com/ltn22/pyang")

        return key_mapping
