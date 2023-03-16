#!/bin/bash

# Set yang modules location
MODULES="/usr/local/share/yang/modules/"

show_help() {
    echo "Convert XML to JSON yang config file. Requires yanglint module."
    echo "Usage: ./xml_to_json.sh model.yang input.xml [output.json]"
    echo "Edit file to set yang modules location (MODULES)."
}

YANG=$1
XML=$2
JSON=$3


if [[ "$YANG" == "" || "$YANG" == "-h" || "$YANG" == "--help" ]]; then
    echo "No YANG datamodel specified."
    show_help
    exit
fi
if [ "$XML" = "" ]; then
    echo "No XML config file specified."
    show_help
    exit
fi

if [ "$JSON" = "" ]; then
    JSON="data.json"
fi

yanglint --format=json --type=config --output=$JSON $YANG $XML -p $MODULES

echo "Saved config to $JSON."
