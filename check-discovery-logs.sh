#!/bin/bash

echo "Checking SNMP worker logs for interface discovery..."
echo ""

docker logs wardops-worker-snmp-prod --tail 200 | grep -i -A5 -B5 "interface\|discover\|61bfeaa1"

echo ""
echo ""
echo "Checking for any Python exceptions..."
docker logs wardops-worker-snmp-prod --tail 200 | grep -i -A10 "exception\|error\|traceback"
