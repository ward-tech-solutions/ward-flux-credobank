# Backend Fix Required: Alert Trigger Data

## Issue
The Alert Rules page shows "Never triggered" for all rules despite 873 active alerts being present in the system.

## Root Cause
The `AlertRule` model in the database currently has these fields for tracking trigger history:
- `last_triggered_at` (timestamp)
- `trigger_count_24h` (integer)
- `trigger_count_7d` (integer)
- `affected_devices_count` (integer)

However, these fields are **never being populated** when alerts are evaluated and triggered. The alert evaluation logic creates alert instances but doesn't update the corresponding AlertRule record.

## Required Backend Changes

### 1. Update Alert Evaluation Logic
When an alert rule is triggered (i.e., the expression evaluates to true for a device), you need to update the AlertRule record:

**Location**: Wherever alerts are evaluated (likely in a Celery task or API endpoint that processes device status)

**Changes needed**:
```python
from datetime import datetime, timedelta
from sqlalchemy import func

def evaluate_and_trigger_alert(rule: AlertRule, device):
    """Evaluate if a rule matches a device's current state"""

    # Your existing evaluation logic here
    if expression_matches(rule.expression, device):
        # Create the alert instance (existing code)
        create_alert_instance(rule, device)

        # NEW: Update the AlertRule trigger statistics
        now = datetime.utcnow()
        rule.last_triggered_at = now

        # Increment 24h counter
        if rule.trigger_count_24h is None:
            rule.trigger_count_24h = 1
        else:
            rule.trigger_count_24h += 1

        # Increment 7d counter
        if rule.trigger_count_7d is None:
            rule.trigger_count_7d = 1
        else:
            rule.trigger_count_7d += 1

        db.session.commit()
```

### 2. Add Periodic Counter Reset Task
The 24h and 7d counters need to be reset periodically. Add a Celery beat task:

**New file**: `tasks/reset_alert_counters.py`
```python
from celery import shared_task
from datetime import datetime, timedelta
from models import AlertRule
from database import db

@shared_task
def reset_24h_counters():
    """Reset 24h trigger counters for all rules"""
    AlertRule.query.update({
        AlertRule.trigger_count_24h: 0
    })
    db.session.commit()

@shared_task
def reset_7d_counters():
    """Reset 7d trigger counters for all rules"""
    AlertRule.query.update({
        AlertRule.trigger_count_7d: 0
    })
    db.session.commit()
```

**Update Celery beat schedule**:
```python
# In your celery config
beat_schedule = {
    # ... existing tasks ...
    'reset-24h-alert-counters': {
        'task': 'tasks.reset_alert_counters.reset_24h_counters',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'reset-7d-alert-counters': {
        'task': 'tasks.reset_alert_counters.reset_7d_counters',
        'schedule': crontab(day_of_week=1, hour=0, minute=0),  # Weekly on Monday
    },
}
```

### 3. Update affected_devices_count
This should be calculated when displaying the Alert Rules page:

**Option A**: Calculate on query (slower but accurate)
```python
@app.route('/api/alert-rules')
def get_alert_rules():
    rules = AlertRule.query.all()

    for rule in rules:
        # Count unique devices that currently match this rule
        affected_count = db.session.query(func.count(func.distinct(Alert.device_id)))\
            .filter(Alert.rule_id == rule.id)\
            .filter(Alert.status == 'active')\
            .scalar()

        rule.affected_devices_count = affected_count

    return jsonify([rule.to_dict() for rule in rules])
```

**Option B**: Update when alert status changes (faster queries)
```python
def update_alert_status(alert, new_status):
    """Update alert status and recalculate affected devices"""
    alert.status = new_status

    # Recalculate affected devices for the rule
    affected_count = db.session.query(func.count(func.distinct(Alert.device_id)))\
        .filter(Alert.rule_id == alert.rule_id)\
        .filter(Alert.status == 'active')\
        .scalar()

    alert.rule.affected_devices_count = affected_count
    db.session.commit()
```

## Testing the Fix

After implementing these changes:

1. **Trigger some alerts** by creating test conditions
2. **Verify the AlertRule record updates**:
   ```python
   rule = AlertRule.query.first()
   print(f"Last triggered: {rule.last_triggered_at}")
   print(f"24h count: {rule.trigger_count_24h}")
   print(f"7d count: {rule.trigger_count_7d}")
   ```
3. **Check the frontend** - The "Last Triggered" column should show timestamps instead of "Never triggered"
4. **Verify expandable rows** - Analytics cards should show non-zero values

## Priority
**HIGH** - This is user-facing data inconsistency that undermines trust in the monitoring system.

## Related Files
- Frontend: `/frontend/src/pages/AlertRules.tsx` (already updated with UI)
- Backend: Alert evaluation logic (needs update)
- Backend: Celery tasks (needs new reset tasks)
- Backend: API routes (may need affected_devices_count calculation)
