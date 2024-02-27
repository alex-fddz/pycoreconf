#!/bin/bash

# Set yang modules location
MODULES="/usr/local/share/yang/modules/"

show_help() {
    echo "Generate SID file from YANG data model. Requires ltn22/pyang module."
    echo "Usage: ./gen_sid.sh model.yang [entry_point] [block_size]"
    echo "Edit file to set yang modules location (MODULES)."
}

YANG=$1
ENTRY=$2
SIZE=$3

if [[ "$YANG" == "" || "$YANG" == "-h" || "$YANG" == "--help" ]]; then
    echo "No YANG datamodel specified."
    show_help
    exit
fi
if [ "$ENTRY" = "" ]; then
    echo "Using experimental range: 60 000 (50)."
    ENTRY=60000
    SIZE=50
else
    if [ "$SIZE" = "" ]; then
        echo "Assigning 50 IDs."
        SIZE=50
    fi
fi

pyang --sid-generate-file $ENTRY:$SIZE --sid-list --sid-extension $YANG -p $MODULES

echo "Done."
