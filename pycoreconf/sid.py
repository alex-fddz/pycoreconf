import json

class ModelSID:
    """
    Class to define methods for reading a YANG model SID file and hold values.
    """

    def __init__(self, sid_file):
        self.sid_file = sid_file
        self.sids = None
        self.types = None

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
        items = obj["items"] # list
        for item in items:
            sids[item["identifier"]] = item["sid"]
            if "type" in item.keys():
                types[item["identifier"]] = item["type"]

        return sids, types


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
        items = obj["items"] # list
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
        items = obj["items"] # list
        for item in items:
            sids[item["identifier"]] = item["sid"]

        return sids
