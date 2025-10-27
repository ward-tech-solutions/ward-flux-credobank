#!/bin/bash

# UI Stress Test Runner for Ward-Ops
# Replace SERVER_IP with your Credobank server IP address

echo "🚀 Ward-Ops UI Stress Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# IMPORTANT: Replace this with your actual Credobank server IP
SERVER_IP="YOUR_SERVER_IP_HERE"

if [ "$SERVER_IP" = "YOUR_SERVER_IP_HERE" ]; then
    echo "❌ ERROR: Please edit this script and set SERVER_IP to your Credobank server IP"
    echo ""
    echo "Example:"
    echo "  SERVER_IP=\"10.x.x.x\"  # Replace with actual IP"
    echo ""
    exit 1
fi

# Check if requests library is installed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "❌ ERROR: requests library not found"
    echo ""
    echo "Install it with:"
    echo "  pip3 install requests"
    echo ""
    exit 1
fi

echo "📋 Configuration:"
echo "   Server URL:  http://$SERVER_IP:5001"
echo "   Users:       10 (test1 - test10)"
echo "   Duration:    5 minutes"
echo ""
echo "Press ENTER to start the test (or Ctrl+C to cancel)"
read

# Run the stress test
python3 scripts/stress_test_ui.py \
    --url "http://$SERVER_IP:5001" \
    --users 10 \
    --duration 300

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Stress test completed!"
echo ""
echo "📊 Check the aggregate statistics above to verify:"
echo "   - Success Rate should be > 99%"
echo "   - Avg Response Time should be < 1s"
echo "   - No failed requests"
echo ""
