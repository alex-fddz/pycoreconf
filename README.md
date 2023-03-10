# pycoreconf

Open-source implementation library of CORECONF (CoAP Management Interface) for Python.

## What is CORECONF?

The [CoAP Management Interface (CORECONF)](https://datatracker.ietf.org/doc/html/draft-ietf-core-comi-11) is a network management protocol designed for constrained devices and networks. It uses the CoAP protocol to maintain a low message footprint, follows a stateless client-server architecture, and manages resources and properties defined in a [YANG](https://www.rfc-editor.org/rfc/rfc7950) data model.

CORECONF uses a CBOR mapping of YANG to keep message sizes extremely low, and substitutes the nodes' names for [YANG Schema Item iDentifiers (SIDs)](200~https://datatracker.ietf.org/doc/html/draft-ietf-core-sid-15). These are numeric values that are assigned to the model in ranges, so that each node has a corresponding SID. Moreover, the SIDs are assigned in a delta structure, which contributes to achieving a very small memory footprint.

## Installation

From source:

```
git clone https://github.com/alex-fddz/pycoreconf.git
cd pycoreconf
python3 setup.py install   # this might require root access
```

### To uninstall

```
pip uninstall pycoreconf
```

## API and Usage

Import the module with:

```
import pycoreconf as cc
```

### `cc.set_sid_file(sid_file)`

- `sid_file`: Path to model's .sid file

Returns nothing. All other methods depend on this configuration. 

### `cc.add_modules_path(ietf_modules_loc)`

- `ietf_modules_loc`: Path or list of paths where IETF and other modules used in the YANG model may be found.

Returns nothing. Required for decoded configuration data validation.

### `cc.set_model_description_file(desc_file)`

- `desc_file`: YANG data model description JSON file (manually created).

Returns nothing. Required for decoded configuration data validation.

### `cc.json_to_coreconf(json_file)`

- `json_file`: Path to JSON file holding the configuration data.

Returns (CBOR encoded) CORECONF configuration data.

### `cc.coreconf_to_libconf(coreconf_data, save_loc)`

- `coreconf_data`: (CBOR encoded) CORECONF configuration data.
- `save_loc`: File name (location) for .cfg file to be saved.

Returns nothing. Saves the decoded configuration data in `libconf` format in the specified save location. Requires a defined model description file to validate the decoded configuration data.

### `cc.toCORECONF(config_data)` 

- `config_data`: Python dictionary holding configuration data.

Returns (CBOR encoded) CORECONF configuration data.

### `cc.toJSON(coreconf_data)`

- `coreconf_data`: (CBOR encoded) CORECONF configuration data.

Returns decoded configuration data as a Python Dictionary.

### `cc.js2cc(json_file, sid_file='model.sid')`

- `json_file`: Path to JSON file holding the configuration data.
- `sid_file` (Optional): Path to model's .sid file. Takes configured .sid file as default.

Returns nothing. Writes CORECONF data in a .cbor file.

### `cc.cc2cfg(coreconf_file, sid_file='model.sid')`

- `coreconf_file`: Path to .cbor file holding the CORECONF data.
- `sid_file` (Optional): Path to model's .sid file. Takes configured .sid file as default.

Returns nothing. Writes decoded configuration data as a .cfg (libconf) file.

