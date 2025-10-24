#!/usr/bin/env python3
"""Test VictoriaMetrics timestamp format"""
import time
import requests

print("=" * 70)
print("TESTING VICTORIAMETRICS TIMESTAMP FORMATS")
print("=" * 70)

current_time = int(time.time())
print(f"\nCurrent time: {current_time} seconds since epoch")
print(f"Current time in ms: {current_time * 1000}")

# Test 1: Timestamp in milliseconds (current implementation)
print("\n" + "=" * 70)
print("TEST 1: Timestamp in MILLISECONDS (current implementation)")
print("=" * 70)
payload1 = f'test_timestamp_ms{{test="milliseconds"}} 100 {current_time}000\n'
print(f"Payload: {payload1.strip()}")

response1 = requests.post(
    'http://victoriametrics:8428/api/v1/import/prometheus',
    data=payload1.encode('utf-8'),
    headers={"Content-Type": "text/plain"},
    timeout=10
)
print(f"Write status: {response1.status_code}")
if response1.text:
    print(f"Response: {response1.text}")

time.sleep(2)

result1 = requests.get('http://victoriametrics:8428/api/v1/query?query=test_timestamp_ms')
data1 = result1.json()
found1 = len(data1.get("data", {}).get("result", []))
print(f"Query result: {found1} metrics found")
if found1 > 0:
    print(f"✅ MILLISECONDS WORK!")
else:
    print(f"❌ MILLISECONDS DON'T WORK")

# Test 2: Timestamp in seconds
print("\n" + "=" * 70)
print("TEST 2: Timestamp in SECONDS")
print("=" * 70)
payload2 = f'test_timestamp_sec{{test="seconds"}} 200 {current_time}\n'
print(f"Payload: {payload2.strip()}")

response2 = requests.post(
    'http://victoriametrics:8428/api/v1/import/prometheus',
    data=payload2.encode('utf-8'),
    headers={"Content-Type": "text/plain"},
    timeout=10
)
print(f"Write status: {response2.status_code}")
if response2.text:
    print(f"Response: {response2.text}")

time.sleep(2)

result2 = requests.get('http://victoriametrics:8428/api/v1/query?query=test_timestamp_sec')
data2 = result2.json()
found2 = len(data2.get("data", {}).get("result", []))
print(f"Query result: {found2} metrics found")
if found2 > 0:
    print(f"✅ SECONDS WORK!")
else:
    print(f"❌ SECONDS DON'T WORK")

# Test 3: No timestamp (let VM assign)
print("\n" + "=" * 70)
print("TEST 3: NO TIMESTAMP (let VictoriaMetrics assign)")
print("=" * 70)
payload3 = f'test_timestamp_none{{test="none"}} 300\n'
print(f"Payload: {payload3.strip()}")

response3 = requests.post(
    'http://victoriametrics:8428/api/v1/import/prometheus',
    data=payload3.encode('utf-8'),
    headers={"Content-Type": "text/plain"},
    timeout=10
)
print(f"Write status: {response3.status_code}")
if response3.text:
    print(f"Response: {response3.text}")

time.sleep(2)

result3 = requests.get('http://victoriametrics:8428/api/v1/query?query=test_timestamp_none')
data3 = result3.json()
found3 = len(data3.get("data", {}).get("result", []))
print(f"Query result: {found3} metrics found")
if found3 > 0:
    print(f"✅ NO TIMESTAMP WORKS!")
else:
    print(f"❌ NO TIMESTAMP DOESN'T WORK")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)
if found1 > 0:
    print("✅ Use milliseconds (current implementation is correct)")
elif found2 > 0:
    print("⚠️  Use seconds (need to remove '000' suffix)")
elif found3 > 0:
    print("⚠️  Omit timestamp (let VictoriaMetrics assign)")
else:
    print("❌ ALL FORMATS FAILED - there's a different issue!")
print("=" * 70)
