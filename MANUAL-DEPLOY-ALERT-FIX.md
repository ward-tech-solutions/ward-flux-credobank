# MANUAL DEPLOYMENT: Critical Alert Rules Fix

## ⚠️ CRITICAL FIX REQUIRED ON PRODUCTION

The alert rules on production have configuration errors that need immediate fixing:
- Duplicate "High Latency" rules causing conflicts
- SQL-like expressions in ISP rules causing parsing errors: `invalid literal for int() with base 10: '10 AND ip LIKE '%.5'`
- Old unused rules still present in database

## 📋 Manual Deployment Steps

### Step 1: Connect to Production Server
```bash
ssh wardops@10.30.25.46
cd /home/wardops/ward-ops
```

### Step 2: Pull Latest Changes from GitHub
```bash
git pull origin main
```

This will get the following new files:
- `monitoring/alert_evaluator_fixed.py` - Fixed alert evaluator without SQL parsing
- `monitoring/celery_app.py` - Updated to use fixed evaluator
- `migrations/fix_alert_rules_production.sql` - Database cleanup script

### Step 3: Fix Database Alert Rules
```bash
# Execute the SQL migration to clean up alert rules
docker exec -i wardops-postgres-prod psql -U wardops -d monitoring < migrations/fix_alert_rules_production.sql

# Verify rules are fixed (should show 8 clean rules)
docker exec wardops-postgres-prod psql -U wardops -d monitoring -c "
SELECT name, expression, severity FROM alert_rules ORDER BY severity, name;"

# Check no duplicates exist (should return empty)
docker exec wardops-postgres-prod psql -U wardops -d monitoring -c "
SELECT name, COUNT(*) FROM alert_rules GROUP BY name HAVING COUNT(*) > 1;"
```

### Step 4: Restart Monitoring Worker
```bash
# Stop and remove old container
docker compose stop worker-monitoring
docker compose rm -f worker-monitoring

# Start with new code
docker compose up -d worker-monitoring

# Check logs for errors
docker logs wardops-worker-monitoring-prod --tail 100 | grep -E "(ERROR|alert_evaluator|Started)"
```

### Step 5: Verify Fix is Working
```bash
# Watch alert evaluation (should run every 10 seconds)
docker logs -f wardops-worker-monitoring-prod | grep "Alert Evaluation Complete"

# Check ISP links are being detected
docker exec wardops-postgres-prod psql -U wardops -d monitoring -c "
SELECT name, ip,
  CASE WHEN down_since IS NULL THEN 'UP'
       ELSE 'DOWN for ' || EXTRACT(EPOCH FROM (NOW() - down_since))::INT || ' seconds'
  END as status
FROM standalone_devices
WHERE ip LIKE '%.5' AND enabled = true;"

# Check active alerts
docker exec wardops-postgres-prod psql -U wardops -d monitoring -c "
SELECT ah.rule_name, ah.severity, sd.name, sd.ip, ah.triggered_at
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE ah.resolved_at IS NULL
ORDER BY ah.severity, ah.triggered_at DESC
LIMIT 10;"
```

## 🔍 What This Fix Does

### 1. Database Cleanup (`fix_alert_rules_production.sql`)
- Removes ALL existing alert rules (clean slate)
- Creates proper rules without SQL expressions:
  - Device Down/Flapping (10-second detection)
  - ISP Link specific rules (for .5 IPs)
  - Performance alerts (latency, packet loss)

### 2. Fixed Alert Evaluator (`alert_evaluator_fixed.py`)
- No SQL expression parsing
- Direct Python logic: `is_isp_link()` checks if IP ends with '.5'
- ISP links get:
  - CRITICAL severity for down/flapping
  - Stricter thresholds (100ms latency, 5% packet loss)
  - 2 status changes trigger flapping (vs 3 for regular devices)

### 3. Updated Celery Config
- Uses `monitoring.alert_evaluator.evaluate_all_alerts`
- Runs every 10 seconds for real-time detection
- Added hourly stale alert cleanup

## ✅ Expected Results After Fix

1. **No More Errors**: The `invalid literal for int()` errors should stop
2. **Clean Alert Rules**: Exactly 8 rules with proper expressions
3. **ISP Link Detection**: Devices with IPs ending in .5 get CRITICAL alerts
4. **10-Second Detection**: Alerts trigger within 10 seconds of device going down
5. **Auto-Resolution**: Alerts clear when devices recover

## 🚨 Alert Rules After Fix

| Rule Name | Severity | Description |
|-----------|----------|-------------|
| ISP Link Down | CRITICAL | ISP link down for 10+ seconds |
| ISP Link Flapping | CRITICAL | ISP link has 2+ status changes in 5 min |
| ISP Link Packet Loss | CRITICAL | ISP link packet loss >5% |
| Device Down | CRITICAL | Device down for 10+ seconds |
| ISP Link High Latency | HIGH | ISP link latency >100ms |
| Device Flapping | HIGH | Device has 3+ status changes in 5 min |
| High Latency | MEDIUM | Device latency >200ms |
| Packet Loss Detected | MEDIUM | Device packet loss >10% |

## 📱 Verification on Web UI

After deployment, check:
1. http://10.30.25.46:5001/alert-rules - Should show 8 clean rules
2. http://10.30.25.46:5001/alerts - Active alerts with proper severities
3. Monitor page - ISP links (IPs ending in .5) should show correct status

## ⚡ Quick Test

To test ISP link alerting:
1. Find an ISP link device (IP ending with .5)
2. If it goes down, should get CRITICAL alert in 10 seconds
3. When it recovers, alert should auto-resolve

## 🆘 If Issues Persist

Check worker logs for specific errors:
```bash
docker logs wardops-worker-monitoring-prod --tail 200 | grep -E "(ERROR|CRITICAL|exception)"
```

The fixed code is already pushed to GitHub and ready for deployment!