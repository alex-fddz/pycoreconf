import json

class ModelSID:
    """
    Class to define methods for reading a YANG model SID file and hold values.
    """

    def __init__(self, *sid_files):
        self.sid_files = sid_files # a tuple of modules' .sid files
        self.sids, self.types = self.getSIDsAndTypes() #req. ltn22/pyang
        self.ids = {v: k for k, v in self.sids.items()} # {sid:id}

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
            items = obj["item"] # list
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

        for sid_file in self.sid_files:
            # Read the contents of the sid/json file
            f = open(sid_file, "r")
            obj = json.load(f)
            f.close()

            # Get items & map identifier : sid
            ids = {} # init
            items = obj["item"] # list
            for item in items:
                ids[item["sid"]] = item["identifier"]

        return ids

    def getSIDs(self):
        """
        Read SID file and return { identifier : sid } dictionary.
        """
        sids = {} # init
        for sid_file in self.sid_files:
            # Read the contents of the sid/json file
            f = open(self.sid_file, "r")
            obj = json.load(f)
            f.close()

            # Get items & map identifier : sid
            items = obj["item"] # list
            for item in items:
                sids[item["identifier"]] = item["sid"]

        return sids
