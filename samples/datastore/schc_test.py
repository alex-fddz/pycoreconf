import cbor2 as cbor

import pycoreconf

def main():
    sid_path = "ietf-schc@2026-02-24.sid"
    ccm = pycoreconf.CORECONFModel(sid_path)

    ds = ccm.create_datastore()

    print(ds)
    print(ds.to_cbor().hex())

    ds["/schc/rule[rule-id-value='10'][rule-id-length='3']"] = {}
    ds["/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='0']"] = {}

    print(ds)
    print(ds.to_cbor().hex())

    # do stupid thigs with the datastore

    ds["/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='0']/entry-index"] += 1


    print(ds)
    print(ds.to_cbor().hex())

    ds["/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='1']/field-id"] = "ietf-schc:fid-ipv6-version"

    print(ds)
    print(ds.to_cbor().hex())
    print(cbor.loads(ds.to_cbor()))



if __name__ == "__main__":
    main()
