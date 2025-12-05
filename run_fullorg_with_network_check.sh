#!/bin/bash

if ! ping -c 1 8.8.8.8 &> /dev/null && ! ping -c 1 1.1.1.1 &> /dev/null; then
    echo "[$(date)] ⚠️  No internet connection - skipping update" >> "/Users/mosesherrera/Desktop/Podio Api Full Org/network_check.log"
    exit 0
fi

echo "[$(date)] ✅ Internet connected - running update" >> "/Users/mosesherrera/Desktop/Podio Api Full Org/network_check.log"
cd "/Users/mosesherrera/Desktop/Podio Api Full Org"
/opt/homebrew/bin/python3 full_org_return.py
