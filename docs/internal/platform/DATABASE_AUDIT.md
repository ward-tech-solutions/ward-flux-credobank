# Ward OPS Database Audit – 2025-10-11

## Summary
- **Primary datastore**: `data/ward_ops.db` (SQLite) – active (counts refreshed 2025-10-11).
- **Legacy/unused files**: `ward_flux.db`, `monitoring.db` – removed from repository on 2025-10-11 after confirming they were empty placeholders.
- **Key risks**:
  - SQLite write contention for concurrent API activity.
  - Multiple DB files increase confusion during migrations/backups.
  - Missing foreign-key constraints and indexes should be reviewed prior to PostgreSQL migration.

## Table Inventory (`data/ward_ops.db`)
| Table | Rows | Notes |
| --- | ---:| --- |
| users | 3 | Admin + seeded accounts |
| organizations | 0 | Unused placeholder |
| system_config | 0 | Persist global config once setup wizard used |
| setup_wizard_state | 0 | Tracks onboarding progress |
| monitored_hostgroups | 6 | Device group metadata |
| georgian_regions | 11 | Region reference data |
| georgian_cities | 82 | City reference data |
| ping_results | 13 179 | Historical ping telemetry |
| traceroute_results | 0 | Placeholder |
| mtr_results | 0 | Placeholder |
| performance_baselines | 0 | Placeholder |
| monitoring_profiles | 2 | Monitoring config profiles |
| snmp_credentials | 1 | SNMP auth settings |
| monitoring_templates | 6 | Template definitions |
| monitoring_items | 0 | Placeholder |
| alert_rules | 4 | User-defined alert rules |
| alert_history | 0 | No alerts fired yet |
| discovery_rules | 0 | Discovery automation not configured |
| discovery_results | 0 | No discovery runs stored |
| metric_baselines | 0 | Placeholder |
| standalone_devices | 875 | Core device inventory |
| discovery_jobs | 0 | Scheduled jobs table |
| network_topology | 0 | Topology data pending |
| discovery_credentials | 0 | Stored credentials table |
| branches | 128 | Branch metadata |

> Row counts captured via `sqlite3 data/ward_ops.db "SELECT COUNT(*) FROM …"` on 2025-10-11. Legacy files inspected with `file` to confirm zero-byte status.

## Observations
- Heavy data resides in `ping_results` and `standalone_devices`. Index review required for query performance (e.g., indexes on `hostid`, `branch`, `last_check`).
- Reference tables (`georgian_regions`, `georgian_cities`) support filtering; ensure they migrate intact.
- Alert/discovery/history tables mostly empty → safe window to adjust schemas before adoption.
- `sqlite_sequence` not listed above but exists for AUTOINCREMENT tracking.

## Legacy Database Files
| File | Status | Notes |
| --- | --- | --- |
| `ward_flux.db` | Removed (2025-10-11) | Historical placeholder; deleted after confirming 0-byte file. |
| `monitoring.db` | Removed (2025-10-11) | Legacy stub; deleted after confirming 0-byte file. |

## Recommendations
1. **Confirm ownership** of legacy DB files; if unused, archive/remove to avoid confusion.
2. **Design PostgreSQL schema** mirroring `ward_ops.db` (see `docs/POSTGRESQL_MIGRATION.md` for migration plan).
3. **Add indexes** pre-migration to reflect required performance (e.g., `CREATE INDEX idx_ping_results_host_time ON ping_results(hostid, checked_at);`).
4. **Enforce foreign keys** (e.g., `standalone_devices.branch_id` → `branches.id`) during migration for data integrity.
5. **Define retention policy** for `ping_results` to prevent runaway growth (move aged data to cold storage).
6. **Automate backups** even before migration (nightly SQLite file snapshot) and document restore drill.

## Next Steps
- Update `docs/POSTGRESQL_MIGRATION.md` with table-by-table mapping (include new indexes/constraints).
- Create GitHub issues:
  - “Validate and retire legacy SQLite databases.”
  - “Design PostgreSQL schema with indexes + foreign keys.”
  - “Implement data retention for telemetry tables.”
- Schedule dry-run migration using sample PostgreSQL instance.

---

*Maintained by Platform Hardening workstream. Refresh counts and notes after significant schema/data changes.*
