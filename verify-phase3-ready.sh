#!/bin/bash
# Quick verification that Phase 3 is ready to deploy

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         PHASE 3 READINESS CHECK                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Phase 2 is working
echo "1️⃣  Checking Phase 2 status..."
VM_COUNT=$(curl -s "http://localhost:8428/api/v1/series?match[]=device_ping_status" 2>/dev/null | jq '.data | length')

if [ "$VM_COUNT" -gt 800 ]; then
    echo "   ✅ Phase 2 working: $VM_COUNT devices writing to VictoriaMetrics"
else
    echo "   ❌ Phase 2 NOT working: Only $VM_COUNT devices in VictoriaMetrics"
    echo "      Expected: 875+ devices"
    exit 1
fi

# Check Phase 3 files exist
echo ""
echo "2️⃣  Checking Phase 3 files..."
if [ -f "deploy-phase3-victoriametrics.sh" ]; then
    echo "   ✅ Deployment script exists"
else
    echo "   ❌ Deployment script missing"
    exit 1
fi

if grep -q "get_latest_ping_for_devices" utils/victoriametrics_client.py 2>/dev/null; then
    echo "   ✅ VM client has Phase 3 methods"
else
    echo "   ❌ VM client missing Phase 3 methods"
    exit 1
fi

if grep -q "PHASE 3" routers/dashboard.py 2>/dev/null; then
    echo "   ✅ Dashboard has Phase 3 changes"
else
    echo "   ❌ Dashboard missing Phase 3 changes"
    exit 1
fi

# Test current API performance (baseline)
echo ""
echo "3️⃣  Testing current API performance (baseline)..."
START=$(date +%s%N)
curl -s "http://localhost:5001/api/v1/dashboard/stats" > /dev/null 2>&1
END=$(date +%s%N)
CURRENT_MS=$(( (END - START) / 1000000 ))
echo "   📊 Current dashboard query: ${CURRENT_MS}ms"
echo "   🎯 Target after Phase 3: <200ms"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ PHASE 3 IS READY TO DEPLOY!                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 To deploy Phase 3, run:"
echo "   ./deploy-phase3-victoriametrics.sh"
echo ""
