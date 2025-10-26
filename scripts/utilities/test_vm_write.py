#!/usr/bin/env python3
"""Test VictoriaMetrics write functionality"""
import time
import sys

# Add app directory to path
sys.path.insert(0, '/app')

from utils.victoriametrics_client import vm_client
import requests

print("=" * 70)
print("VICTORIAMETRICS WRITE TEST")
print("=" * 70)

# Test metrics
metrics = [{
    "metric": "test_format_check",
    "value": 42,
    "labels": {
        "device_id": "test-uuid-123",
        "device_ip": "10.0.0.99",
        "device_name": "TestDevice"
    },
    "timestamp": int(time.time())
}]

# Build payload manually to see format
print("\n1. Building payload...")
default_timestamp = int(time.time())
lines = []
for m in metrics:
    ts = m.get("timestamp", default_timestamp)
    metric_name = m["metric"]
    value = m["value"]

    label_str = ",".join([f'{k}="{v}"' for k, v in m["labels"].items()])
    line = f'{metric_name}{{{label_str}}} {value} {ts}000'
    lines.append(line)
    print(f"   Line: {line}")

payload = "\n".join(lines) + "\n"
print(f"\n2. Full payload (showing special chars):")
print(f"   {repr(payload)}")

# Write using vm_client
print(f"\n3. Writing to VictoriaMetrics at {vm_client.write_url}")
success = vm_client.write_metrics(metrics)
print(f"   Write result: {success}")

# Wait for data to be available
print("\n4. Waiting 2 seconds for data to be indexed...")
time.sleep(2)

# Query it back
print("\n5. Querying VictoriaMetrics...")
query_url = "http://victoriametrics:8428/api/v1/query?query=test_format_check"
print(f"   URL: {query_url}")
result = requests.get(query_url)
print(f"   Status: {result.status_code}")
print(f"   Response: {result.text}")

# Parse response
import json
data = result.json()
if data.get("status") == "success":
    results = data.get("data", {}).get("result", [])
    if results:
        print(f"\n✅ SUCCESS! Found {len(results)} result(s)")
        for r in results:
            print(f"   Metric: {r.get('metric')}")
            print(f"   Value: {r.get('value')}")
    else:
        print(f"\n❌ FAILURE! Query succeeded but returned 0 results")
        print(f"   This means the write format is being rejected silently")
else:
    print(f"\n❌ FAILURE! Query returned error: {data.get('error')}")

print("\n" + "=" * 70)
