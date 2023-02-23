import json

def getIdentifiers(file):
    """
    Read SID file and return { sid : identifier } dictionary.
    """
    # Read the contents of the sid/json file
    f = open(file, "r")
    obj = json.load(f)
    f.close()

    # Get items & map identifier : sid
    ids = {} # init
    items = obj["items"] # list
    for item in items:
        ids[item["sid"]] = item["identifier"]

    return ids


def getSIDsAndTypes(file):
    """
    Read SID file and return { identifier : sid } + { identifier : type } dictionaries.
    """
    # Read the contents of the sid/json file
    f = open(file, "r")
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

def getSIDs(file):
    """
    Read SID file and return { identifier : sid } dictionary.
    """
    # Read the contents of the sid/json file
    f = open(file, "r")
    obj = json.load(f)
    f.close()

    # Get items & map identifier : sid
    sids = {} # init
    items = obj["items"] # list
    for item in items:
        sids[item["identifier"]] = item["sid"]

    return sids


def main():
    import sys

    # Take specified file (arg)
    try:
        file = sys.argv[1]
    except IndexError:
        raise SystemExit(f"Usage: {sys.argv[0]} <file.sid>")

    import pprint
    pp = pprint.PrettyPrinter(indent=2)

    # Convert and pretty-print
    print(file)
    sids, types = getSIDsAndTypes(file)
    pp.pprint(sids)
    pp.pprint(types)

if __name__ == "__main__":
    main()
