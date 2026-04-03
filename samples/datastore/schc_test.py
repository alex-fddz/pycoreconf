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

    # --- _resolve_path: XPath → (SID, keys) ---
    print("\n--- _resolve_path examples ---")

    xpath1 = "/schc/rule[rule-id-value='11'][rule-id-length='3']/entry[entry-index='1']/field-id"
    sid1, keys1 = ds._resolve_path(xpath1)
    print(f"xpath : {xpath1}")
    print(f"  → sid={sid1}, keys={keys1}")

    xpath2 = "/schc/rule[rule-id-value='10'][rule-id-length='3']"
    sid2, keys2 = ds._resolve_path(xpath2)
    print(f"xpath : {xpath2}")
    print(f"  → sid={sid2}, keys={keys2}")

    # --- _create_xpath: (SID, keys) → XPath ---
    print("\n--- _create_xpath examples ---")

    xpath_out1 = ds._create_xpath(sid1, keys=keys1)
    print(f"sid={sid1}, keys={keys1}")
    print(f"  → {xpath_out1}")

    xpath_out2 = ds._create_xpath(sid2, keys=keys2)
    print(f"sid={sid2}, keys={keys2}")
    print(f"  → {xpath_out2}")

    # --- round-trip check ---
    print("\n--- round-trip ---")
    for xpath_in in [xpath1, xpath2]:
        sid, keys = ds._resolve_path(xpath_in)
        xpath_out = ds._create_xpath(sid, keys=keys)
        status = "OK" if xpath_in == xpath_out else "DIFFER"
        print(f"[{status}] {xpath_in}")
        if status == "DIFFER":
            print(f"       got: {xpath_out}")


if __name__ == "__main__":
    main()
