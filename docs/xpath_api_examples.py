#!/usr/bin/env python3
"""
XPath Database API - Examples with Abstract Data Models

This file demonstrates the XPath Database API with abstract, simple examples
using generic node names (a, b, c, etc.) to make concepts clear without
domain-specific complexity.

Each example is self-contained and shows progressively more complex scenarios.
"""

# ==============================================================================
# EXAMPLE 1: Simple Container with Leaves
# ==============================================================================

"""
Model structure:
├── root
│   ├── a (leaf, int)
│   ├── b (leaf, string)
│   └── c (leaf, float)

Example paths:
- /root/a          → Returns integer
- /root/b          → Returns string
- /root/c          → Returns float
"""

def example_1_simple_container():
    """Read and modify simple leaves in a container."""
    print("=" * 70)
    print("EXAMPLE 1: Simple Container with Leaves")
    print("=" * 70)
    
    # Hypothetical usage:
    # db = model.create_database(cbor_data)
    
    # READ operations
    # a = db["/root/a"]              # >>> 42
    # b = db["/root/b"]              # >>> "hello"
    # c = db["/root/c"]              # >>> 3.14
    
    # WRITE operations
    # db["/root/a"] = 100            # Set a to 100
    # db["/root/b"] = "world"        # Set b to "world"
    # db["/root/c"] *= 2             # Multiply c by 2
    
    # Verification
    # assert db["/root/a"] == 100
    # assert db["/root/b"] == "world"
    # assert db["/root/c"] == 6.28
    
    print("""\
Operations:
  db["/root/a"]           → Read leaf 'a'
  db["/root/a"] = 100     → Write to leaf 'a'
  db["/root/a"] += 10     → In-place operators work!

Key points:
  • Direct leaf access possible
  • Simple data type preservation
  • All Python operators supported (+=, -=, *=, etc.)
""")
    print()


# ==============================================================================
# EXAMPLE 2: Single-Level List
# ==============================================================================

"""
Model structure:
├── root
│   └── items (list node)
│       │
│       ├─ List key: id (int)
│       │
│       ├── [id=0]
│       │   ├── data (leaf, string)
│       │   └── count (leaf, int)
│       │
│       ├── [id=1]
│       │   ├── data (leaf, string)
│       │   └── count (leaf, int)
│       │
│       └── [id=2]
│           ├── data (leaf, string)
│           └── count (leaf, int)

Example paths:
- /root/items[id='0']/data         → "Item 0"
- /root/items[id='1']/count        → 42
- /root/items[id='0']              → {"id": 0, "data": "Item 0", "count": 5}
- /root/items                      → [{"id": 0, ...}, {"id": 1, ...}, ...]
"""

def example_2_single_level_list():
    """Read and modify entries in a simple list."""
    print("=" * 70)
    print("EXAMPLE 2: Single-Level List (one key)")
    print("=" * 70)
    
    # hipothetical usage:
    # db = model.create_database(cbor_data)
    
    # READ individual leaf
    # value = db["/root/items[id='1']/data"]     # >>> "Item 1"
    # count = db["/root/items[id='1']/count"]    # >>> 42
    
    # READ entire list entry
    # entry = db["/root/items[id='1']"]
    # # >>> {'id': 1, 'data': 'Item 1', 'count': 42}
    
    # READ entire list
    # all_items = db["/root/items"]
    # # >>> [
    # #     {'id': 0, 'data': 'Item 0', 'count': 5},
    # #     {'id': 1, 'data': 'Item 1', 'count': 42},
    # #     {'id': 2, 'data': 'Item 2', 'count': 17}
    # # ]
    
    # WRITE leaf in list entry
    # db["/root/items[id='1']/data"] = "Modified Item"
    # db["/root/items[id='1']/count"] = 100
    
    # CREATE new entry automatically
    # db["/root/items[id='3']/data"] = "New Item 3"    # Entry created!
    # db["/root/items[id='3']/count"] = 999
    
    print("""\
Operations:
  db["/root/items[id='1']/data"]     → Read leaf in list
  db["/root/items[id='1']"]          → Read entire entry
  db["/root/items"]                  → Read all entries as list
  
  db["/root/items[id='1']/count"] = 100  → Modify leaf
  db["/root/items[id='3']/data"] = "New" → CREATE entry if missing
  db["/root/items[id='1']/count"] += 10  → In-place operators

Key points:
  • Predicates specify list keys: [key='value']
  • Multiple reads return copies (modifications are safe)
  • Missing entries auto-created on write
  • All entries in a list are accessible
""")
    print()


# ==============================================================================
# EXAMPLE 3: List with Multiple Keys
# ==============================================================================

"""
Model structure:
├── root
│   └── measurements (list node)
│       │
│       ├─ List keys: category (string), index (int)
│       │
│       ├── [category='temp'][index='0']
│       │   ├── value (leaf, float)
│       │   └── unit (leaf, string)
│       │
│       ├── [category='temp'][index='1']
│       │   ├── value (leaf, float)
│       │   └── unit (leaf, string)
│       │
│       ├── [category='humidity'][index='0']
│       │   ├── value (leaf, float)
│       │   └── unit (leaf, string)

Example paths:
- /root/measurements[category='temp'][index='0']/value
- /root/measurements[category='humidity'][index='0']/value
- /root/measurements[category='temp'][index='1']
"""

def example_3_list_multiple_keys():
    """Read and modify entries identified by multiple keys."""
    print("=" * 70)
    print("EXAMPLE 3: List with Multiple Keys")
    print("=" * 70)
    
    # hypothetical usage:
    # db = model.create_database(cbor_data)
    
    # READ with multiple predicates (order can vary!)
    # temp = db["/root/measurements[category='temp'][index='0']/value"]
    # # Same as: db["/root/measurements[index='0'][category='temp']/value"]
    # # >>> 23.5
    
    # READ entire entry with multiple keys
    # entry = db["/root/measurements[category='temp'][index='0']"]
    # # >>> {'category': 'temp', 'index': 0, 'value': 23.5, 'unit': 'C'}
    
    # WRITE
    # db["/root/measurements[category='temp'][index='0']/value"] = 25.0
    # db["/root/measurements[category='humidity'][index='0']/value"] = 65.0
    
    # CREATE new entries
    # db["/root/measurements[category='pressure'][index='0']/value"] = 1013.25
    # db["/root/measurements[category='pressure'][index='0']/unit"] = "hPa"
    
    print("""\
Operations:
  Multiple predicates [key1='val1'][key2='val2'][key3='val3']...
  
  db["/root/measurements[category='temp'][index='0']/value"]
  db["/root/measurements[index='0'][category='temp']/value"]  # Order doesn't matter!
  
  # Modify
  db["/root/measurements[category='temp'][index='0']/value"] = 25.0
  
  # Create with multiple keys
  db["/root/measurements[category='pressure'][index='0']/value"] = 1013.25

Key points:
  • Predicate ORDER doesn't matter (converted to model order internally)
  • All keys must be specified (required by YANG)
  • Type conversion happens automatically (strings → ints, etc.)
  • Auto-creation works with multiple keys
""")
    print()


# ==============================================================================
# EXAMPLE 4: Nested Containers (no lists)
# ==============================================================================

"""
Model structure:
├── root
│   └── config
│       └── settings
│           ├── param1 (leaf, int)
│           ├── param2 (leaf, string)
│           └── param3 (leaf, float)

Example paths:
- /root/config/settings/param1
- /root/config/settings
"""

def example_4_nested_containers():
    """Read and modify values in nested containers."""
    print("=" * 70)
    print("EXAMPLE 4: Nested Containers (no lists)")
    print("=" * 70)
    
    # hypothetical usage:
    # db = model.create_database(cbor_data)
    
    # READ individual leaf
    # p1 = db["/root/config/settings/param1"]     # >>> 42
    # p2 = db["/root/config/settings/param2"]     # >>> "config"
    
    # READ entire subtree
    # settings = db["/root/config/settings"]
    # # >>> {'param1': 42, 'param2': 'config', 'param3': 3.14}
    
    # WRITE
    # db["/root/config/settings/param1"] = 100
    # db["/root/config/settings/param3"] *= 2
    
    print("""\
Operations:
  db["/root/config/settings/param1"]
  db["/root/config/settings"]
  db["/root/config"]
  
  db["/root/config/settings/param1"] = 100

Key points:
  • Containers just add path segments
  • No need for predicates (non-list nodes)
  • Can read intermediate containers
  • Works exactly like Example 1 but deeper
""")
    print()


# ==============================================================================
# EXAMPLE 5: Container with Lists (One list per level)
# ==============================================================================

"""
Model structure (most common real-world case):
├── root
│   └── devices (container)
│       └── device (list)
│           │
│           ├─ List key: device_id (int)
│           │
│           ├── [device_id='1']
│           │   └── interfaces (container)
│           │       └── interface (list)
│           │           │
│           │           ├─ List key: ifname (string)
│           │           │
│           │           ├── [ifname='eth0']
│           │           │   ├── type (leaf, string)
│           │           │   └── mtu (leaf, int)
│           │           │
│           │           └── [ifname='eth1']
│           │               ├── type (leaf, string)
│           │               └── mtu (leaf, int)

Example paths:
- /root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']/mtu
- /root/devices/device[device_id='1']/interfaces
- /root/devices
"""

def example_5_containers_with_nested_lists():
    """Read and modify nested list structures."""
    print("=" * 70)
    print("EXAMPLE 5: Containers with Nested Lists")
    print("=" * 70)
    
    # hypothetical usage:
    # db = model.create_database(cbor_data)
    
    # READ nested values
    # mtu = db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']/mtu"]
    # # >>> 1500
    
    # READ intermediate containers
    # eth0 = db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']"]
    # # >>> {'ifname': 'eth0', 'type': 'ethernet', 'mtu': 1500}
    
    # READ entire device
    # device1 = db["/root/devices/device[device_id='1']"]
    # # >>> {
    # #     'device_id': 1,
    # #     'interfaces': {
    # #         'interface': [
    # #             {'ifname': 'eth0', 'type': 'ethernet', 'mtu': 1500},
    # #             {'ifname': 'eth1', 'type': 'ethernet', 'mtu': 9000}
    # #         ]
    # #     }
    # # }
    
    # WRITE at different levels
    # db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']/mtu"] = 9000
    # db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth2']/type"] = "gigabit"
    
    print("""\
Operations:
  Multiple levels with predicates at each list:
  db["/root/devices/device[id='1']/interfaces/interface[ifname='eth0']/mtu"]
         └─ List key 1     └─ List key 2        └─ Leaf value
  
  db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']/mtu"] = 9000

Key points:
  • Predicates appear at each LIST level
  • Containers pass through without special notation
  • Can read at ANY level of hierarchy
  • Creation auto-creates missing entries at all nested levels
  • Most realistic YANG structures follow this pattern
""")
    print()


# ==============================================================================
# EXAMPLE 6: Delete Operations
# ==============================================================================

"""
Same model as Example 5.
"""

def example_6_deletions():
    """Delete leaves and entire list entries."""
    print("=" * 70)
    print("EXAMPLE 6: Delete Operations")
    print("=" * 70)
    
    # hypothetical usage:
    # db = model.create_database(cbor_data)
    
    # DELETE a single leaf
    # del db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']/mtu"]
    # # eth0 still exists, but without mtu field
    
    # DELETE entire interface entry
    # del db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']"]
    # # eth0 is completely removed from the interface list
    
    # DELETE entire device
    # del db["/root/devices/device[device_id='1']"]
    # # device 1 is completely removed
    
    # Verify deletion
    # try:
    #     val = db["/root/devices/device[device_id='1']/interfaces/interface[ifname='eth0']/mtu"]
    # except KeyError:
    #     print("Successfully deleted")
    
    print("""\
Operations:
  del db["/root/devices/device[id='1']/interfaces/interface[ifname='eth0']/mtu"]
      → Deletes ONLY the mtu field, entry still exists
  
  del db["/root/devices/device[id='1']/interfaces/interface[ifname='eth0']"]
      → Deletes entire interface entry, removed from list
  
  del db["/root/devices/device[id='1']"]
      → Deletes entire device entry

Key points:
  • Deletion precision: delete just the field, or the entire entry
  • Dependent on path length
  • Path to leaf field → deletes that field only
  • Path to container/list entry → deletes entire entry
  • Verify with try/except KeyError
""")
    print()


# ==============================================================================
# EXAMPLE 7: Identity References (identityref)
# ==============================================================================

"""
Model structure:
├── root
│   └── sensors (list node)
│       │
│       ├─ List keys: sensor_id (int), sensor_type (identityref)
│       │
│       ├── [sensor_id='1'][sensor_type='temperature']
│       │   ├── reading (leaf, float)
│       │   └── unit (leaf, string)
│       │
│       ├── [sensor_id='2'][sensor_type='humidity']
│       │   ├── reading (leaf, float)
│       │   └── unit (leaf, string)

IMPORTANT: When using identityref values in XPath:
  - Use the IDENTITY NAME (short name)
  - NOT the SID number
  - NOT the module prefix path
  - The API converts automatically!

Example paths:
- /root/sensors[sensor_id='1'][sensor_type='temperature']/reading
- /root/sensors[sensor_id='2'][sensor_type='humidity']/reading

NOT: [sensor_type='module:temperature'] or [sensor_type=42]
"""

def example_7_identity_references():
    """Use identityref values in predicates and reads."""
    print("=" * 70)
    print("EXAMPLE 7: Identity References (identityref)")
    print("=" * 70)
    
    # hypothetical usage:
    # db = model.create_database(cbor_data)
    
    # READ identityref values (returned as YANG names)
    # sensor1 = db["/root/sensors[sensor_id='1'][sensor_type='temperature']"]
    # print(sensor1['sensor_type'])
    # # >>> 'temperature'  ← Readable name, not SID!
    
    # WRITE new entry with identityref key
    # db["/root/sensors[sensor_id='3'][sensor_type='pressure']/reading"] = 1013.25
    # # Entry created with identityref key 'pressure'
    
    # WRITE/MODIFY identityref values
    # db["/root/sensors[sensor_id='1'][sensor_type='temperature']/unit"] = 'Celsius'
    
    print("""\
Operations:
  db["/root/sensors[sensor_id='1'][sensor_type='temperature']/reading"]
                                    └─ Use SHORT identity name!
  
  result = db["/root/sensors[sensor_id='1'][sensor_type='temperature']"]
  print(result['sensor_type'])
  # >>> 'temperature'  (NOT 'module:temperature', NOT SID)
  
  # Create with identityref key
  db["/root/sensors[sensor_id='3'][sensor_type='pressure']/reading"] = 1013.25

Key points:
  • XPath: Use SHORT identity names [sensor_type='temperature']
  • Return values: Also short names, very readable
  • NO SID numbers in XPath
  • Conversion transparent and automatic
  • This is one of the main advantages of this API!
""")
    print()


# ==============================================================================
# EXAMPLE 8: Complete Read-Modify-Save Workflow
# ==============================================================================

def example_8_complete_workflow():
    """Full lifecycle: load, read, modify, verify, save."""
    print("=" * 70)
    print("EXAMPLE 8: Complete Workflow (Read-Modify-Save)")
    print("=" * 70)
    
    print("""\
Typical usage pattern:

    import pycoreconf
    import json

    # 1. SETUP: Create model and load CBOR
    model = pycoreconf.CORECONFModel("schema.sid")
    with open("data.cbor", "rb") as f:
        db = model.create_database(f.read())

    # 2. READ: Inspect current state
    devices = db["/root/devices"]
    print(f"Found {len(devices['device'])} devices")

    # 3. MODIFY: Change values
    for device in devices['device']:
        dev_id = device['device_id']
        db[f"/root/devices/device[device_id='{dev_id}']/status"] = "active"

    # 4. VERIFY: Check modifications
    assert db[f"/root/devices/device[device_id='1']/status"] == "active"
    
    # 5. VIEW: See JSON representation
    json_data = json.loads(db.to_json())
    print(json.dumps(json_data, indent=2))

    # 6. SAVE: Export modified data
    cbor_bytes = db.to_cbor()
    with open("data_modified.cbor", "wb") as f:
        f.write(cbor_bytes)
    
    print("✅ Done!")
""")
    print()


# ==============================================================================
# EXAMPLE 9: Common Patterns
# ==============================================================================

def example_9_common_patterns():
    """Useful code patterns when working with the API."""
    print("=" * 70)
    print("EXAMPLE 9: Common Patterns")
    print("=" * 70)
    
    print("""\
PATTERN 1: Iterate and modify all entries
────────────────────────────────────────
    items_list = db["/root/items"]
    for item in items_list['item']:
        item_id = item['id']
        db[f"/root/items[id='{item_id}']/count"] += 1

PATTERN 2: Safely delete with try/except
──────────────────────────────────────────
    items_list = db["/root/items"]
    for item in items_list['item']:
        item_id = item['id']
        try:
            del db[f"/root/items[id='{item_id}']/optional_field"]
        except KeyError:
            pass  # Field didn't exist, that's ok

PATTERN 3: Check if entry exists
──────────────────────────────────
    try:
        entry = db["/root/devices/device[id='99']"]
        print("Entry exists:", entry)
    except KeyError:
        print("Entry does not exist")

PATTERN 4: Build complex path dynamically
───────────────────────────────────────────
    def get_interface_mtu(device_id, ifname):
        xpath = f"/root/devices/device[device_id='{device_id}']/" \\
                f"interfaces/interface[ifname='{ifname}']/mtu"
        return db[xpath]
    
    mtu = get_interface_mtu('1', 'eth0')

PATTERN 5: Clone/copy an entry
────────────────────────────────
    original = db["/root/items[id='1']"]
    # Make a new copy
    copy_data = original.copy()
    copy_data['id'] = 2
    db["/root/items[id='2']"] = copy_data
    # Or directly with field assignment:
    db["/root/items[id='2']/count"] = original['count']

PATTERN 6: Bulk load keys for later use
─────────────────────────────────────────
    all_items = db["/root/items"]
    item_ids = [item['id'] for item in all_items['item']]
    print(f"Available IDs: {item_ids}")

PATTERN 7: Conditional updates
────────────────────────────────
    devices = db["/root/devices"]
    for device in devices['device']:
        dev_id = device['device_id']
        old_status = db[f"/root/devices/device[device_id='{dev_id}']/status"]
        
        if old_status == "inactive":
            db[f"/root/devices/device[device_id='{dev_id}']/status"] = "active"
            db[f"/root/devices/device[device_id='{dev_id}']/restart_count"] += 1
""")
    print()


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  XPath Database API - Comprehensive Examples".center(68) + "║")
    print("║" + "  Abstract Models (a, b, c, ...)".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")
    
    example_1_simple_container()
    example_2_single_level_list()
    example_3_list_multiple_keys()
    example_4_nested_containers()
    example_5_containers_with_nested_lists()
    example_6_deletions()
    example_7_identity_references()
    example_8_complete_workflow()
    example_9_common_patterns()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print("\nFor practical examples with real data, see:")
    print("  - samples/terraforma_test/main.py")
    print("  - test_multilevel_predicates.py")
    print("\nFor full documentation, see:")
    print("  - XPATH_API_DOCUMENTATION.md")
