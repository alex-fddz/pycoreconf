# pycoreconf

Open-source implementation library of CORECONF (CoAP Management Interface) for Python.

## What is CORECONF?

The [CoAP Management Interface (CORECONF)](https://datatracker.ietf.org/doc/html/draft-ietf-core-comi-11) is a network management protocol designed for constrained devices and networks. It uses the CoAP protocol to maintain a low message footprint, follows a stateless client-server architecture, and manages resources and properties defined in a [YANG](https://www.rfc-editor.org/rfc/rfc7950) data model.

CORECONF uses a CBOR mapping of YANG to keep message sizes extremely low, and substitutes the nodes' names for [YANG Schema Item iDentifiers (SIDs)](200~https://datatracker.ietf.org/doc/html/draft-ietf-core-sid-15). These are numeric values that are assigned to the model in ranges, so that each node has a corresponding SID. Moreover, the SIDs are assigned in a delta structure, which contributes to achieving a very small memory footprint.

## Installation

From PyPI, minimal install or with optional data validation support:

```
pip install pycoreconf
pip install pycoreconf[validation]
```

From source:

```
git clone https://github.com/alex-fddz/pycoreconf.git
cd pycoreconf
python3 setup.py install    # this might require root access
```

For development and testing (venv):

```
git clone https://github.com/alex-fddz/pycoreconf.git
cd pycoreconf
python3 -m venv .venv
source .venv/bin/activate # or .venv\Scripts\activate
pip install -r requirements.txt
```

### To uninstall

```
pip uninstall pycoreconf
```

## Requirements & Setup

- [ltn22/pyang](https://github.com/ltn22/pyang/) module. Allows the generation of the model's SID file including leaves' data types and list key mappings.
- Extended SID file, generated as follows (see `tools/gen_sid.sh`):

    ```
    pyang --sid-generate-file $ENTRY:$SIZE --sid-list --sid-extension $YANG [-p $MODULES]
    ```

    Where:
    - `$ENTRY`: Entry point of allocated YANG SID Range.
    - `$SIZE`: Size of allocated YANG SID Range.
    - `$YANG`: Path to the .yang data model file.
    - `$MODULES`: (Optional) Path to directories containing dependent YANG modules. Include with -p if your model requires additional modules.

    > *Note*: The range of 60,000 to 99,999 (size 40,000) is reserved for experimental YANG modules. The size of the SID range allocated for a YANG module is recommended to be a multiple of 50 and to be at least 33% above the current number of YANG items.

- For data validation against YANG data model(s):
    - A YANG data model description JSON file (see `samples/validation/description.json`).
    - Validation dependency install (`pycoreconf[validation]`).

## Quick Start

```python
import pycoreconf

# Create model with SID file(s)
ccm = pycoreconf.CORECONFModel("model.sid")

# Encode Python dict to CORECONF (CBOR)
cbor_data = ccm.encode({"example:greeting/message": "Hello!"})

# Decode CORECONF back to Python dict
config = ccm.decode(cbor_data)

# Or work with JSON directly
cbor_data = ccm.encode_json('{"example:greeting/message":"Hello!"}')
json_str = ccm.decode_to_json(cbor_data)

# High-level datastore API
ds = ccm.create_datastore({"example:greeting/message": "Hello!"})
ds["/example:greeting/message"] = "World"
cbor_data = ds.to_cbor()
```

## API Reference

### `pycoreconf.CORECONFModel(sid_files, model_description_file=None)`

Creates a CORECONF model object from SID file(s). Core model object for all CORECONF data operations.

- `sid_files`: Path string or list of paths to .sid files.
- `model_description_file`: Optional path to YANG model description JSON for config validation.

### Encoding

- `encode(config: dict) -> bytes` - Encode a Python dict to CORECONF (CBOR).
- `encode_json(json_config: str) -> bytes` - Encode a JSON string or .json file path to CORECONF.

### Decoding

- `decode(cbor_data: bytes, as_rfc7951: bool = False) -> dict` - Decode CORECONF to Python dict.
- `decode_to_json(cbor_data: bytes) -> str` - Decode CORECONF to JSON string (RFC 7951 compliant).

### Validation

- `validate_json(json_config: str)` - Validate a JSON config against the YANG model. Takes an RFC 7951 compliant JSON string or a path to a .json file. Requires `model_description_file` to be set and `pycoreconf[validation]` to be installed. Raises on invalid data.

### Datastores

These methods return a `CORECONFDatastore` instance. See below for usage.

- `create_datastore(data: dict = None)` - Create datastore from dict.
- `create_datastore_from_json(json_config: str)` - Create datastore from JSON.
- `create_datastore_from_cbor(cbor_data: bytes)` - Create datastore from CBOR.

### `CORECONFDatastore`

Uses a simplified XPath-like syntax with predicates (`[key='value']`) for list entries.
Supports standard Python operations (=, +=, del).
See [docs/xpath_api.md](./docs/xpath_api.md) and [docs/xpath_api_examples.py](./docs/xpath_api_examples.py) for more information.

- `ds[path]` - Get/set values using XPath-like paths (e.g. `/container/list[key='value']/leaf`).
- `ds.predicates(path)` - Get list entry key predicates.
- `ds.to_cbor()` - Export to CBOR.
- `ds.to_json()` - Export to JSON string.

## Logging

Pycoreconf uses the logger name `pycoreconf` (Python's standard `logging` module).

To see log output, configure logging in your application:

```python
import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger('pycoreconf').setLevel(logging.DEBUG)
```

## Tests

```
python3 -m unittest discover -s tests/
```

## Changelog

See [CHANGELOG.md](./CHANGELOG.md).
