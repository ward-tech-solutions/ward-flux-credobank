#!/bin/bash

echo "Checking WARD_ENCRYPTION_KEY in container..."
docker exec wardops-worker-snmp-prod env | grep -i encrypt

echo ""
echo "Checking .env file on host..."
if [ -f .env ]; then
    grep -i encrypt .env || echo "No ENCRYPTION_KEY in .env"
else
    echo ".env file not found"
fi

echo ""
echo "Checking if ENCRYPTION_KEY is set in shell..."
echo "ENCRYPTION_KEY=${ENCRYPTION_KEY:-NOT SET}"

echo ""
echo "Testing with a generated key..."
docker exec wardops-worker-snmp-prod python3 -c "
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(f'Generated key example: {key}')
print('')
print('To fix, add this to .env file:')
print(f'ENCRYPTION_KEY={key}')
"
