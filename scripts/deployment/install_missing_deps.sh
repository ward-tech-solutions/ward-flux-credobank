#!/bin/bash

echo "Installing missing Python dependencies for WARD FLUX..."

# Install missing dependencies
pip3 install celery[redis]>=5.3.4
pip3 install redis>=5.0.1
pip3 install pysnmp-lextudio>=5.0.28

echo "Dependencies installed successfully!"
echo ""
echo "To verify installation, run:"
echo "python3 -c \"import celery, redis, pysnmp; print('All dependencies installed successfully!')\""