# WARD FLUX API Quick Start Guide

## Authentication

All API requests require JWT authentication.

### 1. Login
```bash
curl -X POST http://localhost:5001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Use Token in Requests
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET http://localhost:5001/api/v1/devices/standalone/list \
  -H "Authorization: Bearer $TOKEN"
```

---

## Standalone Device Management

### List All Devices
```bash
# All devices
curl -X GET "http://localhost:5001/api/v1/devices/standalone/list" \
  -H "Authorization: Bearer $TOKEN"

# Filter by vendor
curl -X GET "http://localhost:5001/api/v1/devices/standalone/list?vendor=Cisco" \
  -H "Authorization: Bearer $TOKEN"

# Filter by enabled status
curl -X GET "http://localhost:5001/api/v1/devices/standalone/list?enabled=true" \
  -H "Authorization: Bearer $TOKEN"

# Pagination
curl -X GET "http://localhost:5001/api/v1/devices/standalone/list?skip=0&limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Device by ID
```bash
curl -X GET "http://localhost:5001/api/v1/devices/standalone/{device_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### Create Device
```bash
curl -X POST "http://localhost:5001/api/v1/devices/standalone" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Core-Router-01",
    "ip": "192.168.1.1",
    "hostname": "r1.example.com",
    "vendor": "Cisco",
    "device_type": "router",
    "model": "Catalyst 9300",
    "location": "Datacenter-1",
    "description": "Core distribution router",
    "enabled": true,
    "tags": ["production", "core", "critical"],
    "custom_fields": {
      "rack": "A-12",
      "support_contract": "2025-12-31",
      "serial_number": "FCW2234L0WX"
    }
  }'
```

### Update Device
```bash
# Partial update (only send fields you want to change)
curl -X PUT "http://localhost:5001/api/v1/devices/standalone/{device_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "location": "Datacenter-2",
    "tags": ["production", "core", "critical", "updated"]
  }'
```

### Delete Device
```bash
curl -X DELETE "http://localhost:5001/api/v1/devices/standalone/{device_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### Search Devices
```bash
# Full-text search across name, ip, hostname, vendor, model, description
curl -X GET "http://localhost:5001/api/v1/devices/standalone/search?q=cisco" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Statistics & Analytics

### Summary Statistics
```bash
curl -X GET "http://localhost:5001/api/v1/devices/standalone/stats/summary" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "total_devices": 156,
  "enabled_devices": 142,
  "disabled_devices": 14,
  "by_vendor": {
    "Cisco": 78,
    "Fortinet": 45,
    "Juniper": 23,
    "HP": 10
  },
  "by_type": {
    "router": 45,
    "switch": 67,
    "firewall": 34,
    "server": 10
  }
}
```

### Vendor Statistics
```bash
curl -X GET "http://localhost:5001/api/v1/devices/standalone/stats/by_vendor" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Available Vendors
```bash
curl -X GET "http://localhost:5001/api/v1/devices/standalone/vendors" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Available Device Types
```bash
curl -X GET "http://localhost:5001/api/v1/devices/standalone/types" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Bulk Operations

### Bulk Create Devices
```bash
curl -X POST "http://localhost:5001/api/v1/devices/standalone/bulk/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "name": "Switch-01",
      "ip": "10.0.1.10",
      "vendor": "Cisco",
      "device_type": "switch",
      "enabled": true
    },
    {
      "name": "Switch-02",
      "ip": "10.0.1.11",
      "vendor": "Cisco",
      "device_type": "switch",
      "enabled": true
    }
  ]'
```

Response:
```json
{
  "created_count": 2,
  "devices": [...]
}
```

### Bulk Enable Devices
```bash
curl -X POST "http://localhost:5001/api/v1/devices/standalone/bulk/enable" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["device-uuid-1", "device-uuid-2", "device-uuid-3"]'
```

### Bulk Disable Devices
```bash
curl -X POST "http://localhost:5001/api/v1/devices/standalone/bulk/disable" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["device-uuid-1", "device-uuid-2", "device-uuid-3"]'
```

---

## Python Examples

### Using requests library

```python
import requests

BASE_URL = "http://localhost:5001"

# Login
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    data={"username": "admin", "password": "admin123"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
token = response.json()["access_token"]

# Headers for authenticated requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# List devices
devices = requests.get(
    f"{BASE_URL}/api/v1/devices/standalone/list",
    headers=headers
).json()

print(f"Total devices: {len(devices)}")

# Create device
new_device = {
    "name": "Test-Router",
    "ip": "10.0.0.1",
    "vendor": "Cisco",
    "device_type": "router",
    "enabled": True
}

response = requests.post(
    f"{BASE_URL}/api/v1/devices/standalone",
    headers=headers,
    json=new_device
)

if response.status_code == 201:
    device = response.json()
    print(f"Created device: {device['name']} (ID: {device['id']})")

# Get statistics
stats = requests.get(
    f"{BASE_URL}/api/v1/devices/standalone/stats/summary",
    headers=headers
).json()

print(f"Total: {stats['total_devices']}")
print(f"By vendor: {stats['by_vendor']}")

# Search
results = requests.get(
    f"{BASE_URL}/api/v1/devices/standalone/search?q=cisco",
    headers=headers
).json()

print(f"Found {len(results)} devices matching 'cisco'")
```

---

## Response Schemas

### StandaloneDeviceResponse
```json
{
  "id": "c1b2c866-2b9d-4c96-96b9-0a22ea9ed424",
  "name": "Core-Router-01",
  "ip": "192.168.1.1",
  "hostname": "r1.example.com",
  "vendor": "Cisco",
  "device_type": "router",
  "model": "Catalyst 9300",
  "location": "Datacenter-1",
  "description": "Core distribution router",
  "enabled": true,
  "discovered_at": null,
  "last_seen": null,
  "tags": ["production", "core", "critical"],
  "custom_fields": {
    "rack": "A-12",
    "support_contract": "2025-12-31"
  },
  "created_at": "2025-10-06T12:34:56",
  "updated_at": "2025-10-06T12:34:56"
}
```

---

## Error Handling

### HTTP Status Codes
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input (e.g., duplicate IP)
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Error Response Format
```json
{
  "detail": "Device with IP 192.168.1.1 already exists"
}
```

### Validation Error
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "ip"],
      "msg": "Input should be a valid string",
      "input": 12345
    }
  ]
}
```

---

## Interactive API Documentation

Visit http://localhost:5001/docs for interactive Swagger UI documentation where you can:
- View all endpoints
- Test API calls directly in the browser
- See request/response schemas
- Generate code snippets

---

## Rate Limiting

Current limits (configurable):
- **Authentication**: 5 requests/minute per IP
- **Read operations**: 100 requests/minute per user
- **Write operations**: 30 requests/minute per user

---

## Best Practices

1. **Always store tokens securely** - Never commit tokens to version control
2. **Use pagination** - Don't fetch all devices at once for large deployments
3. **Handle errors gracefully** - Check status codes and parse error messages
4. **Use bulk operations** - More efficient than individual API calls
5. **Filter at the API level** - Use query parameters instead of fetching and filtering locally
6. **Set reasonable timeouts** - Network operations can take time
7. **Validate input** - Check data before sending to avoid validation errors

---

## Next Steps

- **SNMP Credentials**: Attach SNMP credentials to devices for polling
- **Monitoring Profiles**: Assign monitoring profiles with vendor-specific OIDs
- **Templates**: Use pre-built templates for common device types
- **Auto-Discovery**: Scan networks to automatically discover devices
- **Alerting**: Configure alert rules and notification channels

See [PHASE_4_STANDALONE_COMPLETE.md](PHASE_4_STANDALONE_COMPLETE.md) for complete API reference and architecture documentation.
