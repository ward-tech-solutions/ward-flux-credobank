"""
WARD Tech Solutions - Router Utilities
Shared helper functions for routers
"""
import logging
import asyncio
import concurrent.futures
import sqlite3

logger = logging.getLogger(__name__)

# Thread pool for running sync functions in async context
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


async def run_in_executor(func, *args):
    """Run synchronous function in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


def get_zabbix_client(request):
    """Get Zabbix client from app state"""
    return request.app.state.zabbix


def get_monitored_groupids():
    """Get list of monitored group IDs from database"""
    conn = sqlite3.connect("data/ward_ops.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT groupid FROM monitored_hostgroups WHERE is_active = 1
    """
    )
    groupids = [row["groupid"] for row in cursor.fetchall()]
    conn.close()
    return groupids if groupids else None


def extract_city_from_hostname(hostname):
    """Extract city name from hostname"""
    # Remove IP if present: "Batumi-ATM 10.199.96.163" -> "Batumi-ATM"
    name = hostname.split()[0]

    # Handle special prefixes: "PING-Kabali-AP" -> skip "PING", use "Kabali"
    parts = name.split("-")

    # Skip common prefixes (PING, TEST, PROD, etc.)
    common_prefixes = ["PING", "TEST", "PROD", "DEV", "SW", "RTR"]
    if len(parts) > 1 and parts[0].upper() in common_prefixes:
        city = parts[1]  # Use second part as city
    else:
        city = parts[0]  # Use first part as city

    # Remove numbers: "Batumi1" -> "Batumi"
    city = "".join([c for c in city if not c.isdigit()])

    return city.strip()
