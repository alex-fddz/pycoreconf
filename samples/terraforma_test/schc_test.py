import sys
import os
import json
import random
from datetime import datetime
import cbor2 as cbor
import pprint

# Add parent directory to path to import pycoreconf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pycoreconf

def main():
    sid_path = "ietf-schc@2026-02-24.sid"
    ccm = pycoreconf.CORECONFModel(sid_path)

    db=ccm.loadDB()

    print(db)
    print(db.to_cbor().hex())

    db["/schc/rule[rule-id-value='10'][rule-id-length='3']"] = {}
    db["/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='0']"] = {}

    print(db)
    print(db.to_cbor().hex())

    # do stupid thigs with the DB

    db["/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='0']/entry-index"] += 1


    print(db)
    print(db.to_cbor().hex())

    db["/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='0']/field-id"] = "fid-ipv6-version"

    print(db)



if __name__ == "__main__":
    main()
