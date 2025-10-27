#!/bin/bash

echo "🚀 DEPLOYING ALERT FIX TO PRODUCTION"
echo "====================================="

# Server connection details
SERVER="wardops@10.30.25.46"
REMOTE_DIR="/home/wardops/ward-flux-credobank"

echo ""
echo "📋 This script will:"
echo "1. Pull latest code on server"
echo "2. Run database migration to fix alert rules"
echo "3. Create alerts for all DOWN devices"
echo "4. Rebuild and restart alert workers"
echo ""
echo "Press Enter to continue or Ctrl+C to abort..."
read

echo ""
echo "Step 1: Pulling latest code on server..."
echo "----------------------------------------"
ssh $SERVER "cd $REMOTE_DIR && git pull origin main"

echo ""
echo "Step 2: Running database migration to fix alert rules..."
echo "---------------------------------------------------------"
ssh $SERVER "cd $REMOTE_DIR && docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops < migrations/fix_alert_rules_production.sql"

echo ""
echo "Step 3: Creating alerts for all DOWN devices..."
echo "------------------------------------------------"
ssh $SERVER "cd $REMOTE_DIR && docker exec wardops-worker-monitoring-prod python3 create_alerts_now.py"

echo ""
echo "Step 4: Rebuilding worker containers with fixed code..."
echo "---------------------------------------------------------"
ssh $SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.production-priority-queues.yml stop wardops-worker-alerts-prod wardops-worker-monitoring-prod wardops-celery-beat-prod"
ssh $SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.production-priority-queues.yml build --no-cache wardops-worker-alerts-prod wardops-worker-monitoring-prod wardops-celery-beat-prod"
ssh $SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.production-priority-queues.yml up -d wardops-worker-alerts-prod wardops-worker-monitoring-prod wardops-celery-beat-prod"

echo ""
echo "Step 5: Verifying alerts are working..."
echo "----------------------------------------"
sleep 5
ssh $SERVER "cd $REMOTE_DIR && docker exec wardops-worker-alerts-prod tail -n 20 /app/logs/worker_alerts.log"

echo ""
echo "Step 6: Checking alert summary..."
echo "----------------------------------"
ssh $SERVER "cd $REMOTE_DIR && docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c 'SELECT COUNT(*) as active_alerts, severity, rule_name FROM alert_history WHERE resolved_at IS NULL GROUP BY severity, rule_name ORDER BY severity;'"

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "Check the monitoring dashboard at: http://10.30.25.46:5001/monitor"