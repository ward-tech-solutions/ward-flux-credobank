from zabbix_client import ZabbixClient

zabbix = ZabbixClient()

print("=== TESTING get_all_hosts() ===")
try:
    hosts = zabbix.get_all_hosts()
    print(f"Total hosts returned: {len(hosts)}")

    if hosts:
        print("\nFirst 5 devices:")
        for host in hosts[:5]:
            print(f"  - {host['display_name']} | {host['branch']} | {host['region']} | {host['device_type']}")
    else:
        print("ERROR: No hosts returned!")

    # Count by region
    print("\n=== DEVICES BY REGION ===")
    regions = {}
    for host in hosts:
        region = host['region']
        if region not in regions:
            regions[region] = 0
        regions[region] += 1

    for region, count in sorted(regions.items()):
        print(f"{region}: {count} devices")

    # Count by device type
    print("\n=== DEVICES BY TYPE ===")
    types = {}
    for host in hosts:
        dtype = host['device_type']
        if dtype not in types:
            types[dtype] = 0
        types[dtype] += 1

    for dtype, count in sorted(types.items()):
        print(f"{dtype}: {count} devices")

except Exception as e:
    print(f"ERROR in get_all_hosts(): {e}")
    import traceback

    traceback.print_exc()

print("\n=== TESTING get_devices_by_region('Kvemo Kartli') ===")
try:
    devices = zabbix.get_devices_by_region('Kvemo Kartli')
    print(f"Found {len(devices)} devices in Kvemo Kartli")
    for device in devices[:5]:
        print(f"  - {device['display_name']}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()