#!/usr/bin/env python3
"""
SNMP Poller using CLI snmpwalk/snmpget commands
This is what Zabbix actually uses - rock solid
"""
import subprocess
import re
from typing import List, Dict, Optional

class SNMPCLIPoller:
    """SNMP poller using command-line tools"""

    def __init__(self, timeout: int = 5, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    def walk(self, host: str, oid: str, community: str, version: str = '2c') -> List[Dict[str, str]]:
        """
        SNMP walk using snmpwalk command

        Returns: List of {'oid': '...', 'value': '...'}
        """
        cmd = [
            'snmpwalk',
            f'-v{version}',
            f'-c{community}',
            f'-t{self.timeout}',
            f'-r{self.retries}',
            '-OQn',  # Quick output, numeric OIDs
            host,
            oid
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout * (self.retries + 1)
            )

            if result.returncode != 0:
                return []

            # Parse output
            results = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                # Format: .1.3.6.1.2.1.2.2.1.2.1 = STRING: "FastEthernet0/0"
                match = re.match(r'^(\.[\d\.]+)\s*=\s*\w+:\s*(.+)$', line)
                if match:
                    oid_result = match.group(1)
                    value = match.group(2).strip('"')
                    results.append({'oid': oid_result, 'value': value})

            return results

        except Exception as e:
            print(f"snmpwalk error: {e}")
            return []

    def get(self, host: str, oid: str, community: str, version: str = '2c') -> Optional[str]:
        """
        SNMP get using snmpget command

        Returns: value or None
        """
        cmd = [
            'snmpget',
            f'-v{version}',
            f'-c{community}',
            f'-t{self.timeout}',
            f'-r{self.retries}',
            '-Oqv',  # Quick output, value only
            host,
            oid
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout * (self.retries + 1)
            )

            if result.returncode != 0:
                return None

            return result.stdout.strip().strip('"')

        except Exception as e:
            print(f"snmpget error: {e}")
            return None


# Test it
if __name__ == '__main__':
    poller = SNMPCLIPoller(timeout=5, retries=2)

    print("Testing SNMP GET on 10.195.57.5...")
    sysDescr = poller.get('10.195.57.5', '1.3.6.1.2.1.1.1.0', 'XoNaz-<h')
    if sysDescr:
        print(f"✅ sysDescr: {sysDescr[:100]}")
    else:
        print("❌ Failed")

    print("\nTesting SNMP WALK for interfaces...")
    interfaces = poller.walk('10.195.57.5', '1.3.6.1.2.1.2.2.1.2', 'XoNaz-<h')
    print(f"✅ Found {len(interfaces)} interfaces:")
    for iface in interfaces[:10]:
        print(f"  {iface['oid']} = {iface['value']}")

    if len(interfaces) > 10:
        print(f"  ... and {len(interfaces) - 10} more")
