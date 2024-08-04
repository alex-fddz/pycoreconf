import json

class ModelSID:
    """
    Class to define methods for reading a YANG model SID file and hold values.
    """

    def __init__(self, sid_file):
        self.sid_file = sid_file
        self.sids, self.types, self.name = self.getSIDsAndTypes() #req. ltn22/pyang
        self.ids = {v: k for k, v in self.sids.items()} # {sid:id}
        self.moduleName = self.getModuleName()

    def getModuleName(self):
        """
        Some SID with non-empty module-names are then used to fetch SID names while looking up SID
        """
        f = open(self.sid_file, "r")
        obj = json.load(f)
        f.close()
        moduleName = obj.get("module-name")
        formattedModuleName = "/%s:"%moduleName
        return formattedModuleName

    def getSIDsAndTypes(self):
        """
        Read SID file and return { identifier : sid } + { identifier : type } dictionaries.
        """
        # Read the contents of the sid/json file
        f = open(self.sid_file, "r")
        obj = json.load(f)
        f.close()

        # Get items & map identifier : sid and leafIdentifier : typename
        sids = {} # init
        types = {} # init
        items = obj.get("item") # list
        
        # Old SID models have "items" instead of "item" as key
        if not items:
            items = obj["items"] 

        for item in items:
            sids[item["identifier"]] = item["sid"]
            if "type" in item.keys():
                types[item["identifier"]] = item["type"]

        # tmp while single module support:
        name = obj["module-name"]

        return sids, types, name


    def getIdentifiers(self):
        """
        Read SID file and return { sid : identifier } dictionary.
        """
        # Read the contents of the sid/json file
        f = open(self.sid_file, "r")
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
        # Read the contents of the sid/json file
        f = open(self.sid_file, "r")
        obj = json.load(f)
        f.close()

        # Get items & map identifier : sid
        sids = {} # init
        items = obj["item"] # list
        for item in items:
            sids[item["identifier"]] = item["sid"]

        return sids
