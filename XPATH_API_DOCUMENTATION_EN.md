# XPath Database API - Documentation

## Overview

The **XPath Database API** provides a high-level interface for accessing and modifying CORECONF/CBOR data using XPath-like syntax. This API completely hides the complexity of SIDs (Semantic Identifiers) and CBOR structures.

### Advantages

- ✅ Intuitive path-based interface using XPath
- ✅ Automatic CBOR ↔ JSON conversion
- ✅ Support for YANG identities (identityref) with readable names
- ✅ Native Python operators (=, +=, -=, del, etc.)
- ✅ Automatic list key handling
- ✅ Auto-creation of missing entries

---

## Installation and Setup

### Initialize a CORECONF Model

```python
import pycoreconf

# Create a model from a SID file
model = pycoreconf.CORECONFModel("/path/to/your/model.sid")

# Load CBOR data into a database
with open("data.cbor", "rb") as f:
    cbor_data = f.read()

db = model.loadDB(cbor_data)
```

---

## XPath Syntax

### General Format

```
/root/container[key1='value1'][key2='value2']/leaf
 │    │         └─── Predicates (list keys) ───────┘
 │    │
 │    └─── Segments navigating the YANG tree
 │
 └─── Absolute root
```

### Elements

- **Segments** : YANG element names (containers, lists, leaves)
- **Predicates** : `[key='value']` to identify specific list entries
- **Identities** : identityref values use identity names (not SIDs)

### Examples

```python
# Access a container
db["/root/container"]

# Access a leaf in a simple container
db["/root/container/leaf"]

# Access a list entry (1 key)
db["/items/item[id='1']/value"]

# Access a list entry (2 keys)
db["/measurements/measurement[type='temp'][id='0']/value"]

# Access a list entry with identity
db["/sensors/sensor[category='temperature'][location='room-1']/reading"]
```

---

## API - Reading

### Read a Value

```python
# Read a leaf
value = db["/measurements/measurement[type='solar'][id='0']/value"]
print(value)  # >>> 1050

# Read an entire container
entry = db["/measurements/measurement[type='solar'][id='0']"]
print(entry)
# >>> {
#       'type': 'solar-radiation',  # identityref converted to readable name
#       'id': 0,                     # numeric key
#       'value': 1050,
#       'precision': 2,
#       ...
#     }

# Read an entire branch
all_measurements = db["/measurements"]
```

### Read List Keys (`get_keys`)

`get_keys` returns list-entry key predicates for a list XPath.

```python
filters = db.get_keys("/measurements/measurement")
print(filters)
# ["[type='solar-radiation'][id='0']", ...]

# Build full entry paths from returned predicates
entry_paths = [f"/measurements/measurement{f}" for f in filters]
```

With predicates in input, the function returns a single canonical filter string:

```python
db.get_keys("/measurements/measurement[type='atmos-41-weather-station:solar-radiation'][id='0']")
# ["[type='solar-radiation'][id='0']"]
```

For `identityref` keys, short names are returned when unambiguous; otherwise,
the output keeps the fully qualified `module:identity` form.

For `enum` keys, symbolic names are returned when the SID model provides the mapping.

### Features

- identityref values are **automatically converted** to readable identity names
- Data types are preserved (int, str, etc.)
- A deep copy is returned to prevent accidental modifications

---

## API - Writing

### Write a Simple Value

```python
# Write a leaf in a list
db["/measurements/measurement[type='solar'][id='0']/value"] = 2000

# Verify
assert db["/measurements/measurement[type='solar'][id='0']/value"] == 2000
```

### In-Place Operators

```python
# Increment
db["/measurements/measurement[type='solar'][id='0']/counter"] += 10

# Decrement
db["/measurements/measurement[type='solar'][id='0']/counter"] -= 5

# Multiplication and other operators also supported!
db["/measurements/measurement[type='solar'][id='0']/value"] *= 1.5
```

### Write an Entire Container

```python
new_entry = {
    'type': 'wind-speed',
    'id': 2,
    'value': 450,
    'precision': 1
}

db["/measurements/measurement[type='wind-speed'][id='2']"] = new_entry
```

### Auto-Create Entries

When writing, if a list entry doesn't exist, it is **automatically created**:

```python
# This entry doesn't exist - it will be created!
db["/measurements/measurement[type='humidity'][id='5']/precision"] = 2

# The entry is now:
# {
#   'type': 'humidity',      # initial keys
#   'id': 5,
#   'precision': 2           # the value we wrote
# }

# We can write other fields afterwards:
db["/measurements/measurement[type='humidity'][id='5']/value"] = 650
```

---

## API - Deletion

### Delete a Leaf (Specific Field)

```python
# Delete only the 'precision' field
del db["/measurements/measurement[type='solar'][id='0']/precision"]

# The entry still exists, but without the 'precision' field
entry = db["/measurements/measurement[type='solar'][id='0']"]
# 'precision' is not in entry
```

### Delete an Entire Entry

```python
# Delete the entire entry
del db["/measurements/measurement[type='solar'][id='0']"]

# Reading the entry raises KeyError
try:
    db["/measurements/measurement[type='solar'][id='0']/value"]
except KeyError:
    print("Entry was deleted")
```

---

## Data Conversion

### Export to JSON

```python
# Get a JSON representation
json_str = db.to_json()

# Use with json.loads()
import json
data_dict = json.loads(json_str)
```

### Export to CBOR

```python
# Get binary CBOR data
cbor_bytes = db.to_cbor()

# Save
with open("modified.cbor", "wb") as f:
    f.write(cbor_bytes)
```

---

## Complete Workflow

### Example: Read → Modify → Save

```python
import pycoreconf
import json

# 1. Create model
model = pycoreconf.CORECONFModel("/path/to/model.sid")

# 2. Load data
with open("data.cbor", "rb") as f:
    db = model.loadDB(f.read())

# 3. Read a value
old_value = db["/measurements/measurement[type='temp'][id='0']/value"]
print(f"Old value: {old_value}")

# 4. Modify
db["/measurements/measurement[type='temp'][id='0']/value"] = old_value + 100

# 5. Verify
new_value = db["/measurements/measurement[type='temp'][id='0']/value"]
print(f"New value: {new_value}")

# 6. Inspect JSON
json_data = json.loads(db.to_json())
print(json.dumps(json_data, indent=2))

# 7. Save
cbor_bytes = db.to_cbor()
with open("data_modified.cbor", "wb") as f:
    f.write(cbor_bytes)
```

---

## Key Points - Remember

### ✅ Automatic

| Aspect | Behavior |
|--------|----------|
| **Create entries** | Writing to a non-existent key creates the entry |
| **Convert identities** | SID ↔ Identity name automatically |
| **Handle types** | int, str, etc. preserved and converted correctly |
| **CBOR ↔ JSON** | Transparent, handled internally |

### ⚠️ Important

- Modifications are done **in memory**; call `db.to_cbor()` to save
- List keys **must be specified** in predicates
- identityref values must use the **short name** (not full path)
- A **deep copy** is systematically used to prevent data corruption

---

## Error Handling

### KeyError

```python
try:
    value = db["/invalid/path/that/does/not/exist"]
except KeyError as e:
    print(f"Path not found: {e}")
```

### ValueError

```python
try:
    # Trying to use predicates on non-list elements
    db["/simple_container[key='wrong']/value"]
except ValueError as e:
    print(f"Validation error: {e}")
```

---

## Limitations and Considerations

1. **Flat and hierarchical structures supported**
   - ✅ Simple lists with unique keys
   - ✅ Nested lists (Container A > Lists B > Lists C)
   - ✅ Containers without lists

2. **Currently not supported**
   - ❌ XPath functions (positions, wildcards)
   - ❌ Absolute paths without root
   - ❌ Multiple predicates on same level (`..|..`)

---

## Advanced Examples

### Pattern: Update all sample counts

```python
# Read all measurements
measurements = db["/measurements"]

# Iterate and increment each sample-count
for meas in measurements['measurement']:
    meas_type = meas['type']
    meas_id = meas['id']
    
    # Increment
    db[f"/measurements/measurement[type='{meas_type}'][id='{meas_id}']/sample-count"] += 1
```

### Pattern: Create a series of entries

```python
for i in range(5):
    xpath = f"/items/item[id='{i}']"
    # Writing auto-creates the entry
    db[f"{xpath}/value"] = i * 100
    db[f"{xpath}/label"] = f"Item_{i}"
```

### Pattern: Clean up data

```python
# Delete all 'debug' fields if they exist
for i in range(10):
    try:
        del db[f"/measurements/measurement[type='temp'][id='{i}']/debug"]
    except KeyError:
        pass  # Field doesn't exist, that's fine
```

---

## References

- [YANG RFC 6020](https://tools.ietf.org/html/rfc6020)
- [CORECONF RFC 9363](https://tools.ietf.org/html/rfc9363)
- [SID Assignment IANA](https://www.iana.org/)
