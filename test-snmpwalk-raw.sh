#!/bin/bash
echo "Testing snmpwalk raw output..."
docker exec wardops-worker-snmp-prod snmpwalk -v2c -c 'XoNaz-<h' -t5 -r2 -OQn 10.195.57.5 1.3.6.1.2.1.2.2.1.2 | head -20
