import json
from types import NoneType
from typing import Dict, List, Union

class ModelSID:
    """
    Class to define methods for reading a YANG model SID file and hold values.
    """

    def __init__(self, *sid_files):
        self.sid_files = sid_files # a tuple of modules' .sid files
        self.sids, self.types = self.getSIDsAndTypes() #req. ltn22/pyang
        self.ids = {v: k for k, v in self.sids.items()} # {sid:id}
        self.moduleName = self.getModuleName() # XXX: Remove?
        self.key_mapping: Dict = self._set_key_mapping(sid_filename=sid_files[0]) # XXX: Fix this.

    def getModuleName(self):
        """
        Some SID with non-empty module-names are then used to fetch SID names while looking up SID
        """
        return "/"
        # f = open(self.sid_file, "r")
        # obj = json.load(f)
        # f.close()
        # moduleName = obj.get("module-name")
        # formattedModuleName = "/%s:"%moduleName
        # return formattedModuleName

    def getSIDsAndTypes(self):
        """
        Read SID file and return { identifier : sid } + { identifier : type } dictionaries.
        """
        sids = {} # init
        types = {} # init

        for sid_file in self.sid_files:
            
            # Read the contents of the sid/json files
            f = open(sid_file, "r")
            obj = json.load(f)
            f.close()

            # Get items & map identifier : sid and leafIdentifier : typename
            items = obj.get("item") # list
            if not items: # Old SID models have "items" instead of "item" as key
                items = obj["items"]

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    sids[obj["module-name"] +":"+ item["identifier"]] = item["sid"]

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

        for sid_file in self.sid_files:

            # Read the contents of the sid/json file
            f = open(sid_file, "r")
            obj = json.load(f)
            f.close()

            # Get items & map identifier : sid
            items = obj.get("item") # list
            if not items: # Old SID models have "items" instead of "item" as key
                items = obj["items"]

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    ids[item["sid"]] = obj["module-name"] +":"+ item["identifier"]

                else:
                    ids[item["sid"]] = item["identifier"]

        return ids

    def getSIDs(self):
        """
        Read SID file and return { identifier : sid } dictionary.
        """

        sids = {} # init

        for sid_file in self.sid_files:
            # Read the contents of the sid/json file
            f = open(sid_file, "r")
            obj = json.load(f)
            f.close()

            # Get items & map identifier : sid
            items = obj.get("item") # list
            if not items: # Old SID models have "items" instead of "item" as key
                items = obj["items"]

            for item in items:

                if item["namespace"] == "identity": # save as module-name:identity
                    sids[obj["module-name"] +":"+ item["identifier"]] = item["sid"]

                else:
                    sids[item["identifier"]] = item["sid"]

        return sids

    def _set_key_mapping(self, sid_filename: str) -> Union[Dict, NoneType]:
        with open(file=sid_filename, mode='r') as file:
            obj: Dict = json.load(file)

        key_mapping: Union[Dict, NoneType] = None
        
        try:
            key_mapping = obj['key-mapping']
        except:
            print(f"{sid_filename} sid files has not been generated with the --sid-extention options.\n" \
                  + "Some conversion capabilities may not works. see http://github.com/ltn22/pyang")
        finally:
            return key_mapping
