"""Test utilities: deterministic Zabbix client stub."""
from __future__ import annotations

from typing import List, Dict


class StaticZabbixClient:
    """Provide predictable responses for API tests without relying on a live Zabbix instance."""

    def __init__(self):
        self.zapi = object()
        self._hosts: List[Dict[str, object]] = [
            {
                "hostid": "10101",
                "hostname": "Core-Router-TBS",
                "display_name": "Tbilisi Core Router",
                "branch": "Tbilisi",
                "region": "Tbilisi",
                "ip": "192.0.2.10",
                "device_type": "router",
                "status": "Enabled",
                "available": "Available",
                "ping_status": "Up",
                "ping_response_time": 12,
                "groups": ["Core"],
                "problems": 0,
            },
            {
                "hostid": "10102",
                "hostname": "Batumi-ATM-1",
                "display_name": "Batumi ATM 1",
                "branch": "Batumi",
                "region": "Adjara",
                "ip": "192.0.2.45",
                "device_type": "atm",
                "status": "Enabled",
                "available": "Available",
                "ping_status": "Up",
                "ping_response_time": 25,
                "groups": ["Retail"],
                "problems": 0,
            },
        ]
        self._templates: List[Dict[str, object]] = [
            {"templateid": "2001", "name": "Cisco IOS SNMP"},
            {"templateid": "2002", "name": "Linux Server"},
        ]

    # Host listing helpers -------------------------------------------------

    def get_all_hosts(self, group_ids=None):
        return list(self._hosts)

    def get_devices_by_region(self, region: str):
        return [host for host in self._hosts if host["region"].lower() == region.lower()]

    def get_devices_by_branch(self, branch: str):
        return [host for host in self._hosts if host["branch"].lower() == branch.lower()]

    def get_devices_by_type(self, device_type: str):
        return [host for host in self._hosts if host["device_type"].lower() == device_type.lower()]

    def get_host_details(self, hostid: str):
        return next((host for host in self._hosts if host["hostid"] == hostid), None)

    # Dashboard info -------------------------------------------------------

    def get_dashboard_stats(self):
        return {
            "total_devices": len(self._hosts),
            "online_devices": sum(1 for host in self._hosts if host["ping_status"] == "Up"),
            "offline_devices": sum(1 for host in self._hosts if host["ping_status"] != "Up"),
            "warning_devices": 0,
            "uptime_percentage": 99.9,
            "active_alerts": 0,
            "critical_alerts": 0,
        }

    def get_active_alerts(self):
        return []

    def get_mttr_stats(self):
        return {
            "average_mttr_minutes": 12,
            "incidents_last_30_days": 0,
        }

    # Templates, groups, etc -----------------------------------------------

    def get_all_templates(self):
        return list(self._templates)

    def get_all_groups(self):
        return [
            {"groupid": "1", "name": "Core"},
            {"groupid": "2", "name": "Retail"},
        ]

    # Host mutation helpers used by routers --------------------------------

    def update_host(self, hostid: str, **kwargs):
        return {"success": True, "hostid": hostid, "updated": kwargs}

    def create_host(self, **kwargs):
        return {"success": True, "hostid": "99999", "payload": kwargs}

    def delete_host(self, hostid: str):
        return {"success": True, "hostid": hostid}

    def get_device_ping_history(self, hostid: str, time_from: int):
        return []
