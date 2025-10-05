# 🐛 WARD Tech Solutions - Automated Bug Report

**Generated:** 2025-10-06 00:14:31

## 📊 Scan Statistics

- Files Scanned: **33**
- Lines Scanned: **7006**
- Issue Categories: **7**
- Total Issues: **245**

## 🐛 Issues Found

### Bare Except (10)

- ./routers/auth.py:43 - Bare except clause (catches everything): #     except:
- ./routers/diagnostics.py:57 - Bare except clause (catches everything): except:
- ./routers/diagnostics.py:106 - Bare except clause (catches everything): except:
- ./routers/diagnostics.py:425 - Bare except clause (catches everything): except:
- ./routers/diagnostics.py:432 - Bare except clause (catches everything): except:
- ./routers/websockets.py:38 - Bare except clause (catches everything): except:
- ./routers/websockets.py:42 - Bare except clause (catches everything): except:
- ./routers/websockets.py:95 - Bare except clause (catches everything): except:
- ./routers/websockets.py:204 - Bare except clause (catches everything): except:
- ./routers/websockets.py:274 - Bare except clause (catches everything): except:

### Code Style (22)

- ./setup_wizard.py:236 - Line too long (130 chars)
- ./zabbix_client.py:293 - Line too long (130 chars)
- ./zabbix_client.py:387 - Line too long (131 chars)
- ./network_diagnostics.py:268 - Line too long (121 chars)
- ./main.py:184 - Line too long (124 chars)
- ./main.py:526 - Line too long (126 chars)
- ./main.py:533 - Line too long (126 chars)
- ./main.py:594 - Line too long (126 chars)
- ./main.py:636 - Line too long (131 chars)
- ./main.py:767 - Line too long (132 chars)
- ./main.py:860 - Line too long (126 chars)
- ./routers/bulk.py:106 - Line too long (127 chars)
- ./routers/diagnostics.py:352 - Line too long (124 chars)
- ./routers/diagnostics.py:376 - Line too long (144 chars)
- ./routers/diagnostics.py:392 - Line too long (128 chars)
- ./routers/diagnostics.py:653 - Line too long (130 chars)
- ./routers/diagnostics.py:661 - Line too long (128 chars)
- ./routers/infrastructure.py:84 - Line too long (126 chars)
- ./routers/infrastructure.py:91 - Line too long (126 chars)
- ./routers/infrastructure.py:154 - Line too long (126 chars)
- ./routers/infrastructure.py:196 - Line too long (131 chars)
- ./routers/websockets.py:245 - Line too long (138 chars)

### Dangerous Functions (2)

- ./qa_bug_finder.py:100 - Using eval() or exec(): # 9. eval() or exec() usage (dangerous)
- ./qa_bug_finder.py:103 - Using eval() or exec(): f"{filepath}:{line_num} - Using eval() or exec(): {line.strip()}"

### Missing Error Handling (56)

- ./setup_wizard.py:83 - Dictionary access without error handling: hosts = zapi.host.get(output=["hostid"])
- ./zabbix_client.py:290 - Dictionary access without error handling: ping_data = ping_lookup.get(host['hostid'], {})
- ./zabbix_client.py:295 - Dictionary access without error handling: active_triggers = [t for t in host.get('triggers', []) if int(t.get('value', 0)) == 1]
- ./zabbix_client.py:311 - Dictionary access without error handling: 'ip': host['interfaces'][0]['ip'] if host['interfaces'] else device_info.get('ip', 'N/A'),
- ./zabbix_client.py:317 - Dictionary access without error handling: 'groups': [g['name'] for g in host.get('groups', [])],
- ./zabbix_client.py:368 - Dictionary access without error handling: ping_value = ping_items[0].get('lastvalue', '0')
- ./zabbix_client.py:395 - Dictionary access without error handling: 'ip': host['interfaces'][0]['ip'] if host['interfaces'] else device_info.get('ip', 'N/A'),
- ./zabbix_client.py:400 - Dictionary access without error handling: 'groups': [g['name'] for g in host.get('groups', [])],
- ./zabbix_client.py:402 - Dictionary access without error handling: 'triggers': host.get('triggers', []),
- ./zabbix_client.py:403 - Dictionary access without error handling: 'items': host.get('items', [])[:20],
- ./zabbix_client.py:675 - Dictionary access without error handling: [h for h in hosts if h.get('ping_status') == 'Up' or h.get('available') == 'Available'])
- ./zabbix_client.py:677 - Dictionary access without error handling: [h for h in hosts if h.get('ping_status') == 'Down' or h.get('available') == 'Unavailable'])
- ./zabbix_client.py:679 - Dictionary access without error handling: [h for h in hosts if h.get('ping_status') == 'Unknown' or h.get('available') == 'Unknown'])
- ./zabbix_client.py:750 - Dictionary access without error handling: base = REGION_COORDINATES.get(region, REGION_COORDINATES['Other'])
- ./zabbix_client.py:892 - Dictionary access without error handling: current_status = int(items[0].get('lastvalue', 1))
- ./zabbix_client.py:913 - Dictionary access without error handling: prev_value = int(history[i-1].get('value', 1))
- ./zabbix_client.py:914 - Dictionary access without error handling: curr_value = int(history[i].get('value', 1))
- ./main.py:371 - Dictionary access without error handling: online_devices = len([h for h in devices if h.get('ping_status') == 'Up'])
- ./main.py:372 - Dictionary access without error handling: offline_devices = len([h for h in devices if h.get('ping_status') == 'Down'])
- ./main.py:373 - Dictionary access without error handling: warning_devices = len([h for h in devices if h.get('ping_status') == 'Unknown'])
- ./main.py:516 - Dictionary access without error handling: core_routers = [d for d in devices if d.get('device_type') == 'Core Router']
- ./main.py:517 - Dictionary access without error handling: branch_switches = [d for d in devices if d.get('device_type') in ['Switch', 'L3 Switch', 'Branch Switch']]
- ./main.py:556 - Dictionary access without error handling: branches_by_region[switch.get('branch', 'Unknown')].append(switch)
- ./main.py:612 - Dictionary access without error handling: device_types[device.get('device_type', 'Unknown')].append(device)
- ./main.py:646 - Dictionary access without error handling: branch_switch_in_branch = [s for s in branch_switches if s.get('branch') == branch]
- ./routers/auth.py:85 - Dictionary access without error handling: @router.get("/users", response_model=List[UserResponse])
- ./routers/config.py:49 - Dictionary access without error handling: groups = data.get('groups', [])
- ./routers/config.py:65 - Dictionary access without error handling: (group['groupid'], group['name'], group.get('display_name', group['name'])),
- ./routers/bulk.py:97 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == current_user.region]
- ./routers/bulk.py:102 - Dictionary access without error handling: devices = [d for d in devices if d.get("branch") in allowed_branches]
- ./routers/bulk.py:120 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == current_user.region]
- ./routers/bulk.py:125 - Dictionary access without error handling: devices = [d for d in devices if d.get("branch") in allowed_branches]
- ./routers/diagnostics.py:110 - Dictionary access without error handling: for hop in result.get('hops', []):
- ./routers/diagnostics.py:206 - Dictionary access without error handling: hops = data.get('hops', [])
- ./routers/diagnostics.py:307 - Dictionary access without error handling: device_ips = data.get('device_ips', [])
- ./routers/diagnostics.py:352 - Dictionary access without error handling: return {'results': results, 'total': len(device_ips), 'successful': len([r for r in results if r.get('is_reachable')])}
- ./routers/diagnostics.py:366 - Dictionary access without error handling: device_ips = data.get('device_ips', [])
- ./routers/infrastructure.py:56 - Dictionary access without error handling: devices = [d for d in devices if d.get('region') == current_user.region]
- ./routers/infrastructure.py:61 - Dictionary access without error handling: devices = [d for d in devices if d.get('branch') in allowed_branches]
- ./routers/infrastructure.py:74 - Dictionary access without error handling: core_routers = [d for d in devices if d.get('device_type') == 'Core Router']
- ./routers/infrastructure.py:75 - Dictionary access without error handling: branch_switches = [d for d in devices if d.get('device_type') in ['Switch', 'L3 Switch', 'Branch Switch']]
- ./routers/infrastructure.py:114 - Dictionary access without error handling: branches_by_region[switch.get('branch', 'Unknown')].append(switch)
- ./routers/infrastructure.py:172 - Dictionary access without error handling: device_types[device.get('device_type', 'Unknown')].append(device)
- ./routers/infrastructure.py:206 - Dictionary access without error handling: branch_switch_in_branch = [s for s in branch_switches if s.get('branch') == branch]
- ./routers/zabbix.py:140 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == current_user.region]
- ./routers/zabbix.py:145 - Dictionary access without error handling: devices = [d for d in devices if d.get("branch") in allowed_branches]
- ./routers/dashboard.py:88 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == region]
- ./routers/dashboard.py:94 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == current_user.region]
- ./routers/dashboard.py:99 - Dictionary access without error handling: devices = [d for d in devices if d.get("branch") in allowed_branches]
- ./routers/dashboard.py:104 - Dictionary access without error handling: online_devices = len([h for h in devices if h.get("ping_status") == "Up"])
- ./routers/dashboard.py:105 - Dictionary access without error handling: offline_devices = len([h for h in devices if h.get("ping_status") == "Down"])
- ./routers/dashboard.py:106 - Dictionary access without error handling: warning_devices = len([h for h in devices if h.get("ping_status") == "Unknown"])
- ./routers/reports.py:42 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == current_user.region]
- ./routers/reports.py:47 - Dictionary access without error handling: devices = [d for d in devices if d.get("branch") in allowed_branches]
- ./routers/devices.py:47 - Dictionary access without error handling: devices = [d for d in devices if d.get("region") == current_user.region]
- ./routers/devices.py:52 - Dictionary access without error handling: devices = [d for d in devices if d.get("branch") in allowed_branches]

### Print Statements (105)

- ./init_setup_db.py:12 - Using print() instead of logging: print("Running SQL migrations...")
- ./init_setup_db.py:16 - Using print() instead of logging: print("⚠️  No migrations directory found")
- ./init_setup_db.py:31 - Using print() instead of logging: print(f"  Running {sql_file}...")
- ./init_setup_db.py:39 - Using print() instead of logging: print(f"  ✅ {sql_file} completed")
- ./init_setup_db.py:41 - Using print() instead of logging: print(f"  ⚠️  {sql_file} error (may be already applied): {e}")
- ./init_setup_db.py:44 - Using print() instead of logging: print("✅ SQL migrations completed!")
- ./init_setup_db.py:48 - Using print() instead of logging: print("Creating setup wizard tables...")
- ./init_setup_db.py:53 - Using print() instead of logging: print("✅ Setup tables created successfully!")
- ./init_setup_db.py:54 - Using print() instead of logging: print("\nTables created:")
- ./init_setup_db.py:55 - Using print() instead of logging: print("  - organizations")
- ./init_setup_db.py:56 - Using print() instead of logging: print("  - system_config")
- ./init_setup_db.py:57 - Using print() instead of logging: print("  - setup_wizard_state")
- ./init_setup_db.py:58 - Using print() instead of logging: print("  - users")
- ./migrate_to_postgres.py:21 - Using print() instead of logging: print("🔄 Starting database migration from SQLite to PostgreSQL...")
- ./migrate_to_postgres.py:39 - Using print() instead of logging: print("📊 Creating tables in PostgreSQL...")
- ./migrate_to_postgres.py:47 - Using print() instead of logging: print("✅ Tables created")
- ./migrate_to_postgres.py:54 - Using print() instead of logging: print(f"📦 Migrating table: {table_name}...")
- ./migrate_to_postgres.py:72 - Using print() instead of logging: print(f"   ✅ Migrated {len(rows_data)} rows")
- ./migrate_to_postgres.py:76 - Using print() instead of logging: print(f"   ⚠️  Error migrating {table_name}: {e}")
- ./migrate_to_postgres.py:79 - Using print() instead of logging: print(f"   ℹ️  No data to migrate")
- ./migrate_to_postgres.py:84 - Using print() instead of logging: print(f"\n✅ Migration complete!")
- ./migrate_to_postgres.py:85 - Using print() instead of logging: print(f"   Tables migrated: {tables_migrated}")
- ./migrate_to_postgres.py:86 - Using print() instead of logging: print(f"   Total rows: {total_rows}")
- ./migrate_to_postgres.py:87 - Using print() instead of logging: print(f"   PostgreSQL is now ready to use!")
- ./migrate_to_postgres.py:96 - Using print() instead of logging: print("❌ Error: DATABASE_URL must be set to a PostgreSQL connection string")
- ./migrate_to_postgres.py:97 - Using print() instead of logging: print("   Example: postgresql://user:password@localhost:5432/database")
- ./migrate_to_postgres.py:102 - Using print() instead of logging: print(f"❌ Error: SQLite database not found at {sqlite_path}")
- ./migrate_to_postgres.py:103 - Using print() instead of logging: print("   If this is a fresh installation, no migration is needed.")
- ./migrate_to_postgres.py:107 - Using print() instead of logging: print(f"📍 SQLite source: {sqlite_path}")
- ./migrate_to_postgres.py:108 - Using print() instead of logging: print(f"📍 PostgreSQL target: {postgres_url}")
- ./migrate_to_postgres.py:109 - Using print() instead of logging: print()
- ./migrate_to_postgres.py:115 - Using print() instead of logging: print("❌ Migration cancelled")
- ./zabbix_client.py:176 - Using print() instead of logging: print(f"Loaded {len(rows)} city coordinates from database")
- ./zabbix_client.py:178 - Using print() instead of logging: print(f"Warning: Could not load coordinates from database: {e}")
- ./zabbix_client.py:179 - Using print() instead of logging: print("Using hardcoded coordinates as fallback")
- ./zabbix_client.py:246 - Using print() instead of logging: print(f"Error getting groups: {e}")
- ./zabbix_client.py:251 - Using print() instead of logging: print(f"[DEBUG] Querying Zabbix for hosts with group IDs: {final_group_ids}")
- ./zabbix_client.py:261 - Using print() instead of logging: print(f"[DEBUG] Zabbix returned {len(hosts) if hosts else 0} hosts")
- ./zabbix_client.py:264 - Using print() instead of logging: print("[DEBUG] No hosts found for these groups")
- ./zabbix_client.py:325 - Using print() instead of logging: print(f"Error processing host {host.get('name', 'Unknown')}: {e}")
- ./zabbix_client.py:332 - Using print() instead of logging: print(f"Error getting hosts: {e}")
- ./zabbix_client.py:382 - Using print() instead of logging: print(f"Error getting ping history: {e}")
- ./zabbix_client.py:409 - Using print() instead of logging: print(f"Error getting host details: {e}")
- ./zabbix_client.py:456 - Using print() instead of logging: print(f"Error getting alerts: {e}")
- ./zabbix_client.py:537 - Using print() instead of logging: print(f"Error getting router interfaces for host {hostid}: {e}")
- ./zabbix_client.py:591 - Using print() instead of logging: print(f"Error calculating MTTR: {e}")
- ./zabbix_client.py:715 - Using print() instead of logging: print(f"Error getting dashboard stats: {e}")
- ./zabbix_client.py:925 - Using print() instead of logging: print(f"Error calculating availability for host {hostid}: {e}")
- ./network_diagnostics.py:59 - Using print() instead of logging: print(f"Ping error for {ip_address}: {e}")
- ./network_diagnostics.py:227 - Using print() instead of logging: print(f"Traceroute error for {ip_address}: {e}")
- ./main.py:115 - Using print() instead of logging: print("✓ Default admin user created (username: admin, password: admin123)")
- ./main.py:122 - Using print() instead of logging: print("✓ Admin user role updated to ADMIN")
- ./main.py:124 - Using print() instead of logging: print("✓ Admin user already exists")
- ./main.py:126 - Using print() instead of logging: print(f"Warning: Could not create default admin user: {e}")
- ./main.py:241 - Using print() instead of logging: print("Warning: slowapi not installed. Rate limiting disabled. Install with: pip install slowapi")
- ./main.py:535 - Using print() instead of logging: print(f"[ERROR] Failed to get interfaces for {router['display_name']}: {e}")
- ./main.py:597 - Using print() instead of logging: print(f"[WARN] Could not get interface bandwidth: {e}")
- ./qa_bug_finder.py:147 - Using print() instead of logging: print("\n" + "="*80)
- ./qa_bug_finder.py:148 - Using print() instead of logging: print("🔍 WARD TECH SOLUTIONS - AUTOMATED BUG FINDER REPORT")
- ./qa_bug_finder.py:149 - Using print() instead of logging: print("="*80)
- ./qa_bug_finder.py:151 - Using print() instead of logging: print(f"\n📊 Scan Statistics:")
- ./qa_bug_finder.py:152 - Using print() instead of logging: print(f"   Files Scanned: {self.file_count}")
- ./qa_bug_finder.py:153 - Using print() instead of logging: print(f"   Lines Scanned: {self.line_count}")
- ./qa_bug_finder.py:154 - Using print() instead of logging: print(f"   Issue Categories: {len(self.issues)}")
- ./qa_bug_finder.py:155 - Using print() instead of logging: print(f"   Total Issues: {sum(len(v) for v in self.issues.values())}")
- ./qa_bug_finder.py:158 - Using print() instead of logging: print("\n✅ NO ISSUES FOUND! Code looks clean.")
- ./qa_bug_finder.py:161 - Using print() instead of logging: print("\n" + "="*80)
- ./qa_bug_finder.py:162 - Using print() instead of logging: print("🐛 ISSUES FOUND (sorted by severity):")
- ./qa_bug_finder.py:163 - Using print() instead of logging: print("="*80)
- ./qa_bug_finder.py:186 - Using print() instead of logging: print(f"\n🔴 {category} ({len(issues)} issues):")
- ./qa_bug_finder.py:187 - Using print() instead of logging: print("-" * 80)
- ./qa_bug_finder.py:190 - Using print() instead of logging: print(f"   • {issue}")
- ./qa_bug_finder.py:193 - Using print() instead of logging: print(f"   ... and {len(issues) - 10} more")
- ./qa_bug_finder.py:198 - Using print() instead of logging: print(f"\n⚠️  {category} ({len(issues)} issues):")
- ./qa_bug_finder.py:199 - Using print() instead of logging: print("-" * 80)
- ./qa_bug_finder.py:201 - Using print() instead of logging: print(f"   • {issue}")
- ./qa_bug_finder.py:203 - Using print() instead of logging: print(f"   ... and {len(issues) - 5} more")
- ./qa_bug_finder.py:229 - Using print() instead of logging: print(f"\n📄 Full report saved to: {filename}")
- ./qa_bug_finder.py:235 - Using print() instead of logging: print("🔍 Scanning codebase for potential bugs...")
- ./qa_bug_finder.py:241 - Using print() instead of logging: print("\n" + "="*80)
- ./qa_bug_finder.py:242 - Using print() instead of logging: print("✅ Scan complete!")
- ./qa_bug_finder.py:243 - Using print() instead of logging: print("="*80)
- ./init_db.py:7 - Using print() instead of logging: print("Creating database tables...")
- ./init_db.py:25 - Using print() instead of logging: print("✅ Admin user created successfully!")
- ./init_db.py:26 - Using print() instead of logging: print("   Username: admin")
- ./init_db.py:27 - Using print() instead of logging: print("   Password: admin123")
- ./init_db.py:28 - Using print() instead of logging: print("   ⚠️  Please change this password after first login!")
- ./init_db.py:30 - Using print() instead of logging: print("⚠️  Admin user already exists")
- ./init_db.py:33 - Using print() instead of logging: print("\n✅ Database initialization complete!")
- ./routers/infrastructure.py:93 - Using print() instead of logging: print(f"[ERROR] Failed to get interfaces for {router['display_name']}: {e}")
- ./routers/infrastructure.py:157 - Using print() instead of logging: print(f"[WARN] Could not get interface bandwidth: {e}")
- ./routers/websockets.py:106 - Using print() instead of logging: print(f"Monitor error: {e}")
- ./routers/websockets.py:113 - Using print() instead of logging: print(f"[WS] Router interface connection request for hostid: {hostid}")
- ./routers/websockets.py:117 - Using print() instead of logging: print(f"[WS] WebSocket accepted for router {hostid}")
- ./routers/websockets.py:119 - Using print() instead of logging: print(f"[WS ERROR] Failed to accept WebSocket: {e}")
- ./routers/websockets.py:142 - Using print() instead of logging: print(f"[WS ERROR] Interfaces is not a dict: {type(interfaces)}")
- ./routers/websockets.py:185 - Using print() instead of logging: print(f"Error streaming interfaces for {hostid}: {e}")
- ./routers/websockets.py:198 - Using print() instead of logging: print(f"WebSocket disconnected for router {hostid}")
- ./routers/websockets.py:201 - Using print() instead of logging: print(f"WebSocket error for router {hostid}: {e}")
- ./routers/websockets.py:254 - Using print() instead of logging: print(f"Error checking problems: {e}")
- ./routers/websockets.py:270 - Using print() instead of logging: print(f"WebSocket error: {e}")
- ./routers/dashboard.py:72 - Using print() instead of logging: print(f"[DEBUG] Monitored groups from DB: {monitored_groups}")
- ./routers/dashboard.py:76 - Using print() instead of logging: print("[DEBUG] No monitored groups, getting all hosts")
- ./routers/dashboard.py:81 - Using print() instead of logging: print(f"[DEBUG] Fetching hosts for group IDs: {monitored_groupids}")
- ./routers/dashboard.py:84 - Using print() instead of logging: print(f"[DEBUG] Retrieved {len(devices)} devices from Zabbix")

### TODO/FIXME Comments (2)

- ./qa_bug_finder.py:84 - # 7. TODO/FIXME Comments
- ./qa_bug_finder.py:85 - if re.search(r'#.*TODO|#.*FIXME|#.*HACK|#.*XXX', line, re.IGNORECASE):

### Weak Cryptography (48)

- ./models.py:46 - Weak crypto algorithm: description = Column(String(500), nullable=True)
- ./setup_wizard.py:234 - Weak crypto algorithm: SystemConfig(key="setup_complete", value="true", description="Initial setup completed"),
- ./setup_wizard.py:235 - Weak crypto algorithm: SystemConfig(key="organization_id", value=str(org.id), description="Primary organization ID"),
- ./setup_wizard.py:236 - Weak crypto algorithm: SystemConfig(key="setup_date", value=str(__import__('datetime').datetime.now()), description="Setup completion date")
- ./zabbix_client.py:258 - Weak crypto algorithm: selectTriggers=['triggerid', 'description', 'priority', 'value', 'lastchange'],
- ./zabbix_client.py:343 - Weak crypto algorithm: selectTriggers=['triggerid', 'description', 'priority', 'value', 'lastchange'],
- ./zabbix_client.py:377 - Weak crypto algorithm: sortorder='DESC',
- ./zabbix_client.py:431 - Weak crypto algorithm: output=['triggerid', 'description', 'priority', 'lastchange', 'value'],
- ./zabbix_client.py:436 - Weak crypto algorithm: sortorder='DESC',
- ./zabbix_client.py:444 - Weak crypto algorithm: 'description': trigger['description'],
- ./zabbix_client.py:490 - Weak crypto algorithm: description = iface_part.split('(')[1].rstrip(')') if '(' in iface_part else ''
- ./zabbix_client.py:493 - Weak crypto algorithm: description = ''
- ./zabbix_client.py:498 - Weak crypto algorithm: 'description': description,
- ./zabbix_client.py:506 - Weak crypto algorithm: # Update description if found
- ./zabbix_client.py:507 - Weak crypto algorithm: if description and not interfaces_data[iface_name]['description']:
- ./zabbix_client.py:508 - Weak crypto algorithm: interfaces_data[iface_name]['description'] = description
- ./network_diagnostics.py:213 - Weak crypto algorithm: 'reached_destination': any(h.get('ip') == ip_address for h in hops),
- ./network_diagnostics.py:222 - Weak crypto algorithm: 'reached_destination': False,
- ./network_diagnostics.py:232 - Weak crypto algorithm: 'reached_destination': False,
- ./main.py:145 - Weak crypto algorithm: description="""
- ./main.py:212 - Weak crypto algorithm: response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
- ./main.py:511 - Weak crypto algorithm: nodes = []
- ./main.py:540 - Weak crypto algorithm: nodes.append({
- ./main.py:561 - Weak crypto algorithm: nodes.append({
- ./main.py:588 - Weak crypto algorithm: iface_desc = iface_data.get('description', '').lower()
- ./main.py:589 - Weak crypto algorithm: # Match if interface description contains branch name
- ./main.py:590 - Weak crypto algorithm: if branch_name_clean and branch_name_clean in iface_desc:
- ./main.py:633 - Weak crypto algorithm: nodes.append({
- ./main.py:667 - Weak crypto algorithm: 'nodes': nodes,
- ./main.py:670 - Weak crypto algorithm: 'total_nodes': len(nodes),
- ./main.py:798 - Weak crypto algorithm: # Includes: /api/v1/auth/login, /api/v1/auth/register, /api/v1/auth/me
- ./qa_bug_finder.py:107 - Weak crypto algorithm: if re.search(r'md5|sha1|DES', line, re.IGNORECASE):
- ./routers/diagnostics.py:140 - Weak crypto algorithm: .order_by(PingResult.timestamp.desc())\
- ./routers/diagnostics.py:245 - Weak crypto algorithm: .order_by(MTRResult.timestamp.desc(), MTRResult.hop_number)\
- ./routers/diagnostics.py:370 - Weak crypto algorithm: .order_by(PingResult.timestamp.desc())\
- ./routers/diagnostics.py:635 - Weak crypto algorithm: .order_by(PingResult.timestamp.desc())\
- ./routers/infrastructure.py:69 - Weak crypto algorithm: nodes = []
- ./routers/infrastructure.py:98 - Weak crypto algorithm: nodes.append({
- ./routers/infrastructure.py:119 - Weak crypto algorithm: nodes.append({
- ./routers/infrastructure.py:148 - Weak crypto algorithm: iface_desc = iface_data.get('description', '').lower()
- ./routers/infrastructure.py:149 - Weak crypto algorithm: # Match if interface description contains branch name
- ./routers/infrastructure.py:150 - Weak crypto algorithm: if branch_name_clean and branch_name_clean in iface_desc:
- ./routers/infrastructure.py:193 - Weak crypto algorithm: nodes.append({
- ./routers/infrastructure.py:228 - Weak crypto algorithm: 'nodes': nodes,
- ./routers/infrastructure.py:231 - Weak crypto algorithm: 'total_nodes': len(nodes),
- ./routers/websockets.py:175 - Weak crypto algorithm: 'description': data.get('description', '')
- ./routers/websockets.py:245 - Weak crypto algorithm: 'message': f"{problem.get('hostname', 'Unknown Host')} - {problem.get('description', 'Issue detected')}",
- ./tests/test_comprehensive_qa.py:35 - Weak crypto algorithm: app.dependency_overrides[get_db] = override_get_db

