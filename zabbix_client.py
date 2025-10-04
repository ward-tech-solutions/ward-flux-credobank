from pyzabbix import ZabbixAPI
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import time
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)

REGION_COORDINATES = {
    'Tbilisi': {'lat': 41.7151, 'lng': 44.8271},
    'Kvemo Kartli': {'lat': 41.541, 'lng': 44.961},
    'Kakheti': {'lat': 41.6488, 'lng': 45.6942},
    'Mtskheta-Mtianeti': {'lat': 42.100, 'lng': 44.700},
    'Samtskhe-Javakheti': {'lat': 41.601, 'lng': 43.500},
    'Shida Kartli': {'lat': 42.025, 'lng': 43.950},
    'Imereti': {'lat': 42.265, 'lng': 42.700},
    'Samegrelo': {'lat': 42.520, 'lng': 41.870},
    'Guria': {'lat': 41.990, 'lng': 42.110},
    'Achara': {'lat': 41.641, 'lng': 41.650},
    'Other': {'lat': 42.3154, 'lng': 43.3569},
}

BRANCH_COORDINATES = {
    # Tbilisi districts
    'didube': {'lat': 41.779, 'lng': 44.800},
    'saburtalo': {'lat': 41.723, 'lng': 44.760},
    'vake': {'lat': 41.707, 'lng': 44.751},
    'varketili': {'lat': 41.707, 'lng': 44.883},
    'chughureti': {'lat': 41.732, 'lng': 44.797},
    'samgori': {'lat': 41.704, 'lng': 44.861},
    'isani': {'lat': 41.715, 'lng': 44.819},
    'gldani': {'lat': 41.812, 'lng': 44.802},
    'nadzaladevi': {'lat': 41.744, 'lng': 44.790},
    'temka': {'lat': 41.840, 'lng': 44.808},
    'vazisubani': {'lat': 41.698, 'lng': 44.880},
    'marjanishvili': {'lat': 41.707, 'lng': 44.799},
    'aghmashenebeli': {'lat': 41.733, 'lng': 44.791},
    'digomi': {'lat': 41.782, 'lng': 44.735},
    'dighomi': {'lat': 41.776, 'lng': 44.724},
    'campus': {'lat': 41.716, 'lng': 44.780},
    'lilo': {'lat': 41.676, 'lng': 44.959},
    'mitskevichi': {'lat': 41.731, 'lng': 44.742},

    # Kvemo Kartli
    'bolnisi': {'lat': 41.447, 'lng': 44.535},
    'marneuli': {'lat': 41.488, 'lng': 44.808},
    'rustavi': {'lat': 41.540, 'lng': 44.985},
    'gardabani': {'lat': 41.457, 'lng': 45.093},
    'tetritskaro': {'lat': 41.555, 'lng': 44.460},
    'dmanisi': {'lat': 41.338, 'lng': 44.220},
    'tsalka': {'lat': 41.593, 'lng': 44.102},
    'tskaltubo': {'lat': 42.342, 'lng': 42.598},
    'tsaltubo': {'lat': 42.342, 'lng': 42.598},  # Alternative spelling

    # Kakheti
    'sagarejo': {'lat': 41.732, 'lng': 45.331},
    'gurjaani': {'lat': 41.746, 'lng': 45.802},
    'telavi': {'lat': 41.919, 'lng': 45.473},
    'akhmeta': {'lat': 42.045, 'lng': 45.207},
    'dedoplistskaro': {'lat': 41.463, 'lng': 46.097},
    'lagodekhi': {'lat': 41.825, 'lng': 46.276},
    'sighnaghi': {'lat': 41.622, 'lng': 45.921},
    'kvareli': {'lat': 41.954, 'lng': 45.817},

    # Mtskheta-Mtianeti
    'kaspi': {'lat': 41.920, 'lng': 44.419},
    'dusheti': {'lat': 42.086, 'lng': 44.693},
    'tianeti': {'lat': 42.109, 'lng': 44.972},
    'mtskheta': {'lat': 41.845, 'lng': 44.721},

    # Samtskhe-Javakheti
    'akhaltsikhe': {'lat': 41.639, 'lng': 42.982},
    'borjomi': {'lat': 41.838, 'lng': 43.378},
    'akhalkalaki': {'lat': 41.404, 'lng': 43.484},
    'ninotsminda': {'lat': 41.267, 'lng': 43.590},
    'bakuriani': {'lat': 41.749, 'lng': 43.517},
    'adigeni': {'lat': 41.676, 'lng': 42.697},

    # Shida Kartli
    'gori': {'lat': 41.985, 'lng': 44.113},
    'kareli': {'lat': 42.022, 'lng': 43.895},
    'khashuri': {'lat': 41.994, 'lng': 43.590},
    'kabali': {'lat': 41.8409404111616, 'lng': 46.1262046643526},

    # Imereti
    'kutaisi': {'lat': 42.268, 'lng': 42.718},
    'khoni': {'lat': 42.322, 'lng': 42.420},
    'chiatura': {'lat': 42.294, 'lng': 43.298},
    'sachkhere': {'lat': 42.350, 'lng': 43.410},
    'zestaponi': {'lat': 42.111, 'lng': 43.036},
    'terjola': {'lat': 42.208, 'lng': 42.975},
    'samtredia': {'lat': 42.175, 'lng': 42.334},
    'vani': {'lat': 42.081, 'lng': 42.518},
    'baghdati': {'lat': 42.074, 'lng': 42.822},
    'kharagauli': {'lat': 41.944, 'lng': 43.200},
    'tkibuli': {'lat': 42.349, 'lng': 42.996},
    'ambrolauri': {'lat': 42.521, 'lng': 43.147},

    # Samegrelo-Zemo Svaneti
    'zugdidi': {'lat': 42.509, 'lng': 41.870},
    'poti': {'lat': 42.146, 'lng': 41.671},
    'martvili': {'lat': 42.409, 'lng': 42.379},
    'khobi': {'lat': 42.321, 'lng': 41.902},
    'senaki': {'lat': 42.269, 'lng': 42.067},
    'chkhorotsku': {'lat': 42.531, 'lng': 42.116},
    'abasha': {'lat': 42.210, 'lng': 42.204},
    'mestia': {'lat': 43.045, 'lng': 42.723},

    # Guria
    'ozurgeti': {'lat': 41.925, 'lng': 42.006},
    'lanchkhuti': {'lat': 42.085, 'lng': 41.856},
    'chokhatauri': {'lat': 41.996, 'lng': 42.104},

    # Achara (Adjara)
    'batumi': {'lat': 41.651, 'lng': 41.636},
    'kobuleti': {'lat': 41.821, 'lng': 41.775},
    'khelvachauri': {'lat': 41.586, 'lng': 41.688},
    'khulo': {'lat': 41.643, 'lng': 42.317},
    'shuakhevi': {'lat': 41.621, 'lng': 42.195},
    'keda': {'lat': 41.606, 'lng': 41.940},
}


class ZabbixClient:
    def __init__(self, url: str = None, user: str = None, password: str = None):
        # Load from environment variables (SECURITY FIX) or parameters
        self.url = url or os.getenv("ZABBIX_URL")
        self.user = user or os.getenv("ZABBIX_USER")
        self.password = password or os.getenv("ZABBIX_PASSWORD")

        self.zapi = None
        self._cache = {}
        self._cache_timeout = 30  # seconds
        self._load_coordinates_from_db()

        # Only connect if credentials are available (for SaaS setup wizard mode)
        if all([self.url, self.user, self.password]):
            self.connect()
        else:
            logger.info("Zabbix client initialized without credentials (setup wizard mode)")

    def is_configured(self) -> bool:
        """Check if Zabbix credentials are configured"""
        return all([self.url, self.user, self.password]) and self.zapi is not None

    def reconfigure(self, url: str, user: str, password: str):
        """Reconfigure Zabbix connection with new credentials (after setup wizard)"""
        self.url = url
        self.user = user
        self.password = password
        self.connect()
        logger.info(f"Zabbix client reconfigured for {url}")

    def _load_coordinates_from_db(self):
        """Load city coordinates from database and update BRANCH_COORDINATES"""
        import sqlite3
        try:
            conn = sqlite3.connect('data/ward_ops.db')
            cursor = conn.cursor()
            cursor.execute('SELECT name_en, latitude, longitude FROM georgian_cities WHERE is_active = 1')
            rows = cursor.fetchall()
            conn.close()

            # Update the global BRANCH_COORDINATES with database values
            for name_en, latitude, longitude in rows:
                city_key = name_en.lower()
                BRANCH_COORDINATES[city_key] = {'lat': latitude, 'lng': longitude}

            print(f"Loaded {len(rows)} city coordinates from database")
        except Exception as e:
            print(f"Warning: Could not load coordinates from database: {e}")
            print("Using hardcoded coordinates as fallback")

    def connect(self):
        """Connect to Zabbix API"""
        try:
            self.zapi = ZabbixAPI(self.url.replace('/api_jsonrpc.php', ''))
            self.zapi.login(self.user, self.password)
            print("Successfully connected to Zabbix")
        except Exception as e:
            print(f"Failed to connect to Zabbix: {e}")
            raise

    def _get_cached(self, key):
        """Get cached data if still valid"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_timeout:
                return data
        return None

    def _set_cache(self, key, data):
        """Store data in cache"""
        self._cache[key] = (data, time.time())

    def get_all_hosts(self, group_names=None, group_ids=None, use_cache=True):
        """Get all hosts from specified groups with caching

        Args:
            group_names: List of group names to filter (legacy)
            group_ids: List of group IDs to filter (preferred)
            use_cache: Whether to use cache
        """
        # If group_ids provided, use them directly (preferred method)
        if group_ids is not None:
            cache_key = f"hosts_ids_{','.join(str(gid) for gid in group_ids)}"

            if use_cache:
                cached = self._get_cached(cache_key)
                if cached:
                    return cached

            # Use group_ids directly, no need to query hostgroup
            final_group_ids = [str(gid) for gid in group_ids]
        else:
            # Legacy: use group_names
            if group_names is None:
                group_names = ['Branches', 'AP ICMP', 'ATM ICMP', 'NVR ICMP', 'PayBox ICMP', 'BIOSTAR ICMP']

            cache_key = f"hosts_{','.join(group_names)}"

            if use_cache:
                cached = self._get_cached(cache_key)
                if cached:
                    return cached

            try:
                groups = self.zapi.hostgroup.get(
                    output=['groupid', 'name'],
                    filter={'name': group_names}
                )

                if not groups:
                    return []

                final_group_ids = [g['groupid'] for g in groups]
            except Exception as e:
                print(f"Error getting groups: {e}")
                return []

        try:
            # Get hosts from the group IDs
            print(f"[DEBUG] Querying Zabbix for hosts with group IDs: {final_group_ids}")

            hosts = self.zapi.host.get(
                output=['hostid', 'host', 'name', 'status'],
                groupids=final_group_ids,
                selectInterfaces=['interfaceid', 'ip', 'dns', 'port'],
                selectGroups=['groupid', 'name'],
                selectTriggers=['triggerid', 'description', 'priority', 'value', 'lastchange'],
            )

            print(f"[DEBUG] Zabbix returned {len(hosts) if hosts else 0} hosts")

            if not hosts:
                print("[DEBUG] No hosts found for these groups")
                self._set_cache(cache_key, [])
                return []

            all_host_ids = [h['hostid'] for h in hosts]

            ping_items = []
            if all_host_ids:
                ping_items = self.zapi.item.get(
                    hostids=all_host_ids,
                    filter={'key_': 'icmpping'},
                    output=['hostid', 'itemid', 'lastvalue', 'lastclock']
                )

            ping_lookup = {}
            for item in ping_items:
                ping_lookup[item['hostid']] = {
                    'value': item.get('lastvalue', '0'),
                    'clock': item.get('lastclock')
                }

            result = []
            for host in hosts:
                try:
                    device_info = self.parse_device_name(host['name'])
                    coords = self.compute_coordinates(device_info['region'], device_info['branch'])
                    ping_data = ping_lookup.get(host['hostid'], {})
                    ping_value = ping_data.get('value', '0')
                    ping_status = 'Up' if ping_value == '1' else 'Down' if ping_value == '0' else 'Unknown'
                    availability_status = 'Available' if ping_value == '1' else 'Unavailable' if ping_value == '0' else 'Unknown'

                    active_triggers = [t for t in host.get('triggers', []) if int(t.get('value', 0)) == 1]

                    # Clean display name - remove IP if present
                    clean_name = host['name']
                    parts = clean_name.split()
                    if len(parts) > 1:
                        last_part = parts[-1]
                        if '.' in last_part and any(c.isdigit() for c in last_part):
                            clean_name = ' '.join(parts[:-1])

                    result.append({
                        'hostid': host['hostid'],
                        'hostname': host['host'],
                        'display_name': clean_name,
                        'branch': device_info['branch'],
                        'region': device_info['region'],
                        'ip': host['interfaces'][0]['ip'] if host['interfaces'] else device_info.get('ip', 'N/A'),
                        'status': 'Enabled' if int(host['status']) == 0 else 'Disabled',
                        'available': availability_status,
                        'ping_status': ping_status,
                        'ping_response_time': None,
                        'last_check': ping_data.get('clock'),
                        'groups': [g['name'] for g in host.get('groups', [])],
                        'problems': len(active_triggers),
                        'device_type': device_info['device_type'],
                        'triggers': active_triggers,
                        'latitude': coords['lat'],
                        'longitude': coords['lng']
                    })
                except Exception as e:
                    print(f"Error processing host {host.get('name', 'Unknown')}: {e}")
                    continue

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"Error getting hosts: {e}")
            return []

    def get_host_details(self, hostid):
        """Get detailed information about a specific host"""
        try:
            host = self.zapi.host.get(
                hostids=hostid,
                output=['hostid', 'host', 'name', 'status'],
                selectInterfaces=['interfaceid', 'ip', 'dns', 'port', 'type'],
                selectGroups=['groupid', 'name'],
                selectTriggers=['triggerid', 'description', 'priority', 'value', 'lastchange'],
                selectItems=['itemid', 'name', 'key_', 'lastvalue', 'lastclock', 'units', 'status']
            )

            if not host:
                return None

            host = host[0]

            ping_items = self.zapi.item.get(
                hostids=hostid,
                filter={'key_': 'icmpping'},
                output=['itemid', 'name', 'key_', 'lastvalue', 'lastclock'],
                limit=1
            )

            ping_data = {
                'status': 'Unknown',
                'response_time': None,
                'packet_loss': None,
                'last_check': None,
                'history': []
            }

            if ping_items:
                ping_value = ping_items[0].get('lastvalue', '0')
                ping_data['status'] = 'Up' if ping_value == '1' else 'Down'
                ping_data['last_check'] = ping_items[0].get('lastclock')

                try:
                    history = self.zapi.history.get(
                        itemids=ping_items[0]['itemid'],
                        history=3,
                        sortfield='clock',
                        sortorder='DESC',
                        limit=200
                    )
                    ping_data['history'] = history
                except Exception as e:
                    print(f"Error getting ping history: {e}")

            device_info = self.parse_device_name(host['name'])
            coords = self.compute_coordinates(device_info['region'], device_info['branch'])
            availability = 'Available' if ping_data['status'] == 'Up' else 'Unavailable' if ping_data[
                                                                                                'status'] == 'Down' else 'Unknown'

            return {
                'hostid': host['hostid'],
                'hostname': host['host'],
                'display_name': host['name'],
                'branch': device_info['branch'],
                'region': device_info['region'],
                'ip': host['interfaces'][0]['ip'] if host['interfaces'] else device_info.get('ip', 'N/A'),
                'status': 'Enabled' if int(host['status']) == 0 else 'Disabled',
                'available': availability,
                'ping_status': ping_data['status'],
                'ping_data': ping_data,
                'groups': [g['name'] for g in host.get('groups', [])],
                'interfaces': host['interfaces'],
                'triggers': host.get('triggers', []),
                'items': host.get('items', [])[:20],
                'device_type': device_info['device_type'],
                'latitude': coords['lat'],
                'longitude': coords['lng']
            }
        except Exception as e:
            print(f"Error getting host details: {e}")
            return None

    def get_active_alerts(self):
        """Get all active triggers/alerts"""
        cached = self._get_cached('alerts')
        if cached:
            return cached

        try:
            group_names = ['Branches', 'AP ICMP', 'ATM ICMP', 'NVR ICMP', 'PayBox ICMP', 'BIOSTAR ICMP']
            groups = self.zapi.hostgroup.get(
                output=['groupid'],
                filter={'name': group_names}
            )

            if not groups:
                return []

            group_ids = [g['groupid'] for g in groups]

            triggers = self.zapi.trigger.get(
                output=['triggerid', 'description', 'priority', 'lastchange', 'value'],
                selectHosts=['hostid', 'host', 'name'],
                groupids=group_ids,
                filter={'value': 1},
                sortfield='lastchange',
                sortorder='DESC',
                limit=100
            )

            result = []
            for trigger in triggers:
                result.append({
                    'triggerid': trigger['triggerid'],
                    'description': trigger['description'],
                    'severity': self.get_severity_name(trigger['priority']),
                    'priority': trigger['priority'],
                    'host': trigger['hosts'][0]['name'] if trigger['hosts'] else 'Unknown',
                    'hostid': trigger['hosts'][0]['hostid'] if trigger['hosts'] else None,
                    'time': datetime.fromtimestamp(int(trigger['lastchange'])).strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp': int(trigger['lastchange'])
                })

            self._set_cache('alerts', result)
            return result
        except Exception as e:
            print(f"Error getting alerts: {e}")
            return []

    def get_problems(self):
        """Get current problems (alias for notifications WebSocket)"""
        return self.get_active_alerts()

    def get_router_interfaces(self, hostid):
        """Get network interfaces for a router with bandwidth stats using Zabbix item keys"""
        try:
            # Get all network interface items for this host
            items = self.zapi.item.get(
                hostids=hostid,
                search={'key_': 'net.if'},
                output=['itemid', 'name', 'key_', 'lastvalue', 'lastclock', 'units'],
                sortfield='name'
            )

            # Group items by interface name (extracted from item name)
            interfaces_data = {}

            for item in items:
                item_name = item.get('name', '')
                key = item.get('key_', '')

                # Extract interface name from item name like "Interface Gi0(To_Core_1/0/46): Bits received"
                # or "Interface Gi0/0/0(To_External1_7Port): Operational status"
                if 'Interface ' in item_name and ':' in item_name:
                    # Extract interface part
                    iface_part = item_name.split('Interface ')[1].split(':')[0].strip()

                    # Extract interface name (e.g., "Gi0", "Gi0/0/0", "Cr0/0/8")
                    if '(' in iface_part:
                        iface_name = iface_part.split('(')[0].strip()
                        description = iface_part.split('(')[1].rstrip(')') if '(' in iface_part else ''
                    else:
                        iface_name = iface_part
                        description = ''

                    if iface_name not in interfaces_data:
                        interfaces_data[iface_name] = {
                            'name': iface_name,
                            'description': description,
                            'status': 'unknown',
                            'bandwidth_in': 0,
                            'bandwidth_out': 0,
                            'errors_in': 0,
                            'errors_out': 0
                        }

                    # Update description if found
                    if description and not interfaces_data[iface_name]['description']:
                        interfaces_data[iface_name]['description'] = description

                    # Parse different item types based on key
                    lastvalue = item.get('lastvalue', '0')

                    try:
                        if 'ifOperStatus' in key or 'Operational status' in item_name:
                            # 1 = up, 2 = down
                            interfaces_data[iface_name]['status'] = 'up' if lastvalue == '1' else 'down'

                        elif 'ifHCInOctets' in key or 'Bits received' in item_name:
                            # Convert from bits/sec (Zabbix stores as change per second)
                            interfaces_data[iface_name]['bandwidth_in'] = int(float(lastvalue or 0))

                        elif 'ifHCOutOctets' in key or 'Bits sent' in item_name:
                            interfaces_data[iface_name]['bandwidth_out'] = int(float(lastvalue or 0))

                        elif 'ifInErrors' in key or 'Inbound packets with errors' in item_name:
                            interfaces_data[iface_name]['errors_in'] = int(float(lastvalue or 0))

                        elif 'ifOutErrors' in key or 'Outbound packets with errors' in item_name:
                            interfaces_data[iface_name]['errors_out'] = int(float(lastvalue or 0))

                    except (ValueError, TypeError) as e:
                        continue

            return interfaces_data

        except Exception as e:
            print(f"Error getting router interfaces for host {hostid}: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_mttr_stats(self):
        """Calculate MTTR (Mean Time To Repair) statistics"""
        try:
            hosts = self.get_all_hosts()

            total_downtime = 0
            downtime_events = 0
            mttr_by_region = {}
            mttr_by_type = {}

            for host in hosts:
                if host.get('triggers'):
                    for trigger in host['triggers']:
                        if int(trigger.get('value', 0)) == 1:
                            downtime_events += 1
                            event_time = int(trigger.get('lastchange', 0))
                            duration = time.time() - event_time
                            total_downtime += duration

                            region = host['region']
                            dtype = host['device_type']

                            if region not in mttr_by_region:
                                mttr_by_region[region] = {'total': 0, 'count': 0}
                            mttr_by_region[region]['total'] += duration
                            mttr_by_region[region]['count'] += 1

                            if dtype not in mttr_by_type:
                                mttr_by_type[dtype] = {'total': 0, 'count': 0}
                            mttr_by_type[dtype]['total'] += duration
                            mttr_by_type[dtype]['count'] += 1

            avg_mttr = (total_downtime / downtime_events / 60) if downtime_events > 0 else 0

            region_mttr = {}
            for region, data in mttr_by_region.items():
                region_mttr[region] = round(data['total'] / data['count'] / 60, 2) if data['count'] > 0 else 0

            type_mttr = {}
            for dtype, data in mttr_by_type.items():
                type_mttr[dtype] = round(data['total'] / data['count'] / 60, 2) if data['count'] > 0 else 0

            return {
                'avg_mttr_minutes': round(avg_mttr, 2),
                'total_incidents': downtime_events,
                'mttr_by_region': region_mttr,
                'mttr_by_type': type_mttr
            }
        except Exception as e:
            print(f"Error calculating MTTR: {e}")
            return {}

    def get_all_groups(self):
        """Get all host groups"""
        try:
            groups = self.zapi.hostgroup.get(
                output=['groupid', 'name'],
                sortfield='name'
            )
            return groups
        except Exception as e:
            return []

    def get_all_templates(self):
        """Get all templates"""
        try:
            templates = self.zapi.template.get(
                output=['templateid', 'host', 'name'],
                sortfield='name'
            )
            return templates
        except Exception as e:
            return []

    def create_host(self, hostname, visible_name, ip_address, group_ids, template_ids):
        """Create a new host in Zabbix"""
        try:
            groups = [{'groupid': gid} for gid in group_ids]
            templates = [{'templateid': tid} for tid in template_ids]

            result = self.zapi.host.create(
                host=hostname,
                name=visible_name,
                interfaces=[{
                    'type': 1,
                    'main': 1,
                    'useip': 1,
                    'ip': ip_address,
                    'dns': '',
                    'port': '10050'
                }],
                groups=groups,
                templates=templates
            )

            self._cache.clear()
            return {
                'success': True,
                'hostid': result['hostids'][0],
                'message': f'Host {visible_name} created successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating host: {str(e)}'
            }

    def update_host(self, hostid, **kwargs):
        """Update host properties"""
        try:
            self.zapi.host.update(hostid=hostid, **kwargs)
            self._cache.clear()
            return {'success': True, 'message': 'Host updated successfully'}
        except Exception as e:
            return {'success': False, 'message': f'Error updating host: {str(e)}'}

    def delete_host(self, hostid):
        """Delete a host"""
        try:
            self.zapi.host.delete(hostid)
            self._cache.clear()
            return {'success': True, 'message': 'Host deleted successfully'}
        except Exception as e:
            return {'success': False, 'message': f'Error deleting host: {str(e)}'}

    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        try:
            hosts = self.get_all_hosts()
            alerts = self.get_active_alerts()

            total_devices = len(hosts)
            online_devices = len(
                [h for h in hosts if h.get('ping_status') == 'Up' or h.get('available') == 'Available'])
            offline_devices = len(
                [h for h in hosts if h.get('ping_status') == 'Down' or h.get('available') == 'Unavailable'])
            warning_devices = len(
                [h for h in hosts if h.get('ping_status') == 'Unknown' or h.get('available') == 'Unknown'])

            device_types = {}
            for host in hosts:
                dt = host['device_type']
                if dt not in device_types:
                    device_types[dt] = {'total': 0, 'online': 0, 'offline': 0}
                device_types[dt]['total'] += 1
                if host.get('ping_status') == 'Up' or host.get('available') == 'Available':
                    device_types[dt]['online'] += 1
                elif host.get('ping_status') == 'Down' or host.get('available') == 'Unavailable':
                    device_types[dt]['offline'] += 1

            regions_stats = {}
            for host in hosts:
                region = host['region']
                if region not in regions_stats:
                    regions_stats[region] = {'total': 0, 'online': 0, 'offline': 0}
                regions_stats[region]['total'] += 1
                if host.get('ping_status') == 'Up' or host.get('available') == 'Available':
                    regions_stats[region]['online'] += 1
                elif host.get('ping_status') == 'Down' or host.get('available') == 'Unavailable':
                    regions_stats[region]['offline'] += 1

            return {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': offline_devices,
                'warning_devices': warning_devices,
                'uptime_percentage': round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2),
                'active_alerts': len(alerts),
                'critical_alerts': len([a for a in alerts if a['severity'] in ['High', 'Disaster']]),
                'device_types': device_types,
                'regions_stats': regions_stats
            }
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return {}

    def get_devices_by_region(self, region):
        """Get devices filtered by Georgian region"""
        all_hosts = self.get_all_hosts()
        return [h for h in all_hosts if h['region'] == region]

    def get_devices_by_branch(self, branch):
        """Get devices filtered by branch name"""
        all_hosts = self.get_all_hosts()
        return [h for h in all_hosts if branch.lower() in h['branch'].lower()]

    def get_devices_by_type(self, device_type):
        """Get devices filtered by type"""
        all_hosts = self.get_all_hosts()
        return [h for h in all_hosts if h['device_type'] == device_type]

    @staticmethod
    def compute_coordinates(region, branch=None):
        """Return stable coordinates for a region/branch"""
        normalized_branch = (branch or '').strip().lower()

        # First, try to find exact branch coordinates
        if normalized_branch in BRANCH_COORDINATES:
            coords = BRANCH_COORDINATES[normalized_branch]
            return {'lat': coords['lat'], 'lng': coords['lng']}

        # For unrecognized branches like 'treasury', 'headoffice', use Tbilisi coordinates
        # since they should be in Tbilisi by default
        if region == 'Tbilisi' and normalized_branch:
            # Use main Tbilisi coordinates for unlisted branches
            return {'lat': REGION_COORDINATES['Tbilisi']['lat'], 'lng': REGION_COORDINATES['Tbilisi']['lng']}

        # Return region-level coordinates as fallback
        base = REGION_COORDINATES.get(region, REGION_COORDINATES['Other'])
        return base.copy()

    @staticmethod
    def parse_device_name(hostname):
        """Parse device name and extract info"""
        region_mapping = {
            'Didube': 'Tbilisi', 'Saburtalo': 'Tbilisi', 'Vake': 'Tbilisi',
            'Varketili': 'Tbilisi', 'Chughureti': 'Tbilisi', 'Samgori': 'Tbilisi',
            'Isani': 'Tbilisi', 'Gldani': 'Tbilisi', 'Nadzaladevi': 'Tbilisi',
            'Temka': 'Tbilisi', 'Vazisubani': 'Tbilisi', 'Marjanishvili': 'Tbilisi',
            'Aghmashenebeli': 'Tbilisi', 'Digomi': 'Tbilisi', 'Dighomi': 'Tbilisi',
            'Campus': 'Tbilisi', 'Lilo': 'Tbilisi', 'Mitskevichi': 'Tbilisi',
            'Bolnisi': 'Kvemo Kartli', 'Marneuli': 'Kvemo Kartli',
            'Rustavi': 'Kvemo Kartli', 'Gardabani': 'Kvemo Kartli',
            'Tetritskaro': 'Kvemo Kartli', 'Dmanisi': 'Kvemo Kartli',
            'Tsalka': 'Kvemo Kartli',
            'Sagarejo': 'Kakheti', 'Gurjaani': 'Kakheti', 'Telavi': 'Kakheti',
            'Akhmeta': 'Kakheti', 'Dedoplistskaro': 'Kakheti', 'Lagodekhi': 'Kakheti',
            'Sighnaghi': 'Kakheti', 'Kvareli': 'Kakheti', 'Tsnori': 'Kakheti',
            'Kaspi': 'Mtskheta-Mtianeti', 'Dusheti': 'Mtskheta-Mtianeti',
            'Tianeti': 'Mtskheta-Mtianeti', 'Mtskheta': 'Mtskheta-Mtianeti',
            'Stepantsminda': 'Mtskheta-Mtianeti',
            'Akhaltsikhe': 'Samtskhe-Javakheti', 'Borjomi': 'Samtskhe-Javakheti',
            'Akhalkalaki': 'Samtskhe-Javakheti', 'Ninotsminda': 'Samtskhe-Javakheti',
            'Bakuriani': 'Samtskhe-Javakheti', 'Adigeni': 'Samtskhe-Javakheti',
            'Akhalqalaqi': 'Samtskhe-Javakheti',
            'Gori': 'Shida Kartli', 'Kareli': 'Shida Kartli',
            'Khashuri': 'Shida Kartli', 'Kabali': 'Shida Kartli',
            'Kutaisi': 'Imereti', 'Khoni': 'Imereti', 'Chiatura': 'Imereti',
            'Sachkhere': 'Imereti', 'Zestaponi': 'Imereti', 'Zestafoni': 'Imereti',
            'Terjola': 'Imereti', 'Samtredia': 'Imereti', 'Vani': 'Imereti',
            'Baghdati': 'Imereti', 'Kharagauli': 'Imereti', 'Tkibuli': 'Imereti',
            'Ambrolauri': 'Imereti', 'Tskaltubo': 'Imereti', 'Tsaltubo': 'Imereti',
            'Tsageri': 'Imereti',
            'Zugdidi': 'Samegrelo', 'Poti': 'Samegrelo', 'Martvili': 'Samegrelo',
            'Khobi': 'Samegrelo', 'Senaki': 'Samegrelo', 'Chkhorotsku': 'Samegrelo',
            'Abasha': 'Samegrelo', 'Mestia': 'Samegrelo', 'Tsalenjikha': 'Samegrelo',
            'Ozurgeti': 'Guria', 'Lanchkhuti': 'Guria', 'Chokhatauri': 'Guria',
            'Batumi': 'Achara', 'Kobuleti': 'Achara', 'Khelvachauri': 'Achara',
            'Khulo': 'Achara', 'Shuakhevi': 'Achara', 'Keda': 'Achara', 'Qeda': 'Achara',
        }

        hostname_lower = hostname.lower()

        device_type = 'Switch'
        if '-atm' in hostname_lower or 'atm-' in hostname_lower or 'atm ' in hostname_lower:
            device_type = 'ATM'
        elif '-nvr' in hostname_lower or 'nvr-' in hostname_lower or 'nvr ' in hostname_lower:
            device_type = 'NVR'
        elif '-paybox' in hostname_lower or 'paybox-' in hostname_lower or 'paybox ' in hostname_lower:
            device_type = 'Paybox'
        elif '-ap' in hostname_lower or 'ap-' in hostname_lower or 'ap ' in hostname_lower:
            device_type = 'Access Point'
        elif 'biostar' in hostname_lower:
            device_type = 'Biostar'
        elif '881' in hostname or 'c1121' in hostname or 'c1111' in hostname:
            device_type = 'Router'
        elif 'asr' in hostname_lower:
            device_type = 'Core Router'
        elif 'dr_' in hostname_lower:
            device_type = 'Disaster Recovery'

        branch_name = hostname
        if branch_name.startswith('PING-'):
            branch_name = branch_name[5:]

        parts = branch_name.replace(' - ', '-').split('-')
        if parts:
            branch_name = parts[0]

        for suffix in ['_1', '_2', '1', '2', '3', '4', '5']:
            if branch_name.endswith(suffix):
                branch_name = branch_name[:-len(suffix)]

        ip = None
        import re
        ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', hostname)
        if ip_match:
            ip = ip_match.group()

        region = None
        for key, val in region_mapping.items():
            if key.lower() in branch_name.lower():
                region = val
                break

        # Default to Tbilisi for unrecognized names (Treasury, Headoffice, etc.)
        if region is None:
            region = 'Tbilisi'

        return {
            'branch': branch_name,
            'region': region,
            'ip': ip,
            'device_type': device_type
        }

    @staticmethod
    def get_availability_status(available):
        """Convert availability code to text"""
        status_map = {
            '0': 'Unknown',
            '1': 'Available',
            '2': 'Unavailable'
        }
        return status_map.get(str(available), 'Unknown')

    @staticmethod
    def get_severity_name(priority):
        """Convert priority number to severity name"""
        severity_map = {
            '0': 'Not classified',
            '1': 'Information',
            '2': 'Warning',
            '3': 'Average',
            '4': 'High',
            '5': 'Disaster'
        }
        return severity_map.get(str(priority), 'Unknown')
