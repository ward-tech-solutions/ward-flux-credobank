# PostgreSQL Schema Plan (Draft)

Date: 2025-10-11  
Owner: Platform Hardening

This document captures the proposed PostgreSQL structures that replace the legacy SQLite schema. The goal is to give the schema-design issue a running start and highlight questions that should be resolved before final DDL generation.

The accompanying draft SQL lives in `migrations/postgres/001_core_schema.sql`. The notes below map each high-priority table to its columns, constraints, and migration considerations.

## 1. Core Reference Tables

### `organizations`
- `id SERIAL PK`
- Branding + Zabbix connection fields.
- JSONB column `monitored_groups` keeps the existing array semantics.
- Indexes: implicit PK.

### `system_config`
- Key/value store. `key` remains unique for fast lookups.

### `setup_wizard_state`
- Boolean flags representing wizard progress. No FKs.

## 2. Identity & Access

### `users`
- `id SERIAL PK` (integer) with unique `username` / `email` indexes.
- Role stored as string to avoid enum migration friction.
- `organization_id` becomes a nullable FK to `organizations(id)`.
- JSON fields (`dashboard_layout`) remain JSONB in Postgres.
- SQLite nullable `branches` column remains text; can later be normalized if desired.

## 3. Branch Mapping

### `branches`
- Switched to `UUID` PKs (matches application expectations).
- Indexed on `region` and `is_active` for monitor queries.
- `device_count` preserved (calculated field; consider trigger later).

### `monitored_hostgroups`
- Records Zabbix host group mappings. `groupid` unique with active index.

### `georgian_regions` / `georgian_cities`
- Keep seed data and relational link (`georgian_cities.region_id`).
- Latitude/longitude stored as `NUMERIC(9,6)` for precision.

## 4. Device Inventory

### `standalone_devices`
- UUID PK, optional FK to `branches(id)`.
- JSONB fields for tags/custom metadata.
- Indexes on `branch_id`, `device_type`, `device_subtype`, `enabled`.
- SSH configuration preserved (port/user/flag).
- IP remains non-null but **not** unique (current dataset contains duplicate IPs; revisit after cleanup).

### `ping_results`
- `BIGSERIAL` PK for large growth.
- Indexes on `device_ip` and `timestamp` to support historical queries.
- Consider composite index `(device_ip, timestamp DESC)` during implementation.

### `performance_baselines` & `metric_baselines`
- `performance_baselines` keeps per-device aggregate thresholds.
- `metric_baselines` mirrors monitoring.models definition (UUID PK, computed stats). Index on `device_id` added.

## 5. Monitoring & Templates

### `monitoring_profiles`
- UUID PK. `mode` stored as string (enum can be enforced later).

### `monitoring_templates`
- JSONB columns for template items and triggers.
- `is_builtin` flag retained alongside `is_default` to match existing SQLite schema.
- `created_by` remains UUID (no FK because existing data stores UUID-like strings).
- Indexes handled via unique name constraint.

### `monitoring_items`
- UUID PK with FK to `standalone_devices` (cascade on delete) and optional FK to templates.
- Index on `device_id` for query speed.

### `snmp_credentials`
- FK to `standalone_devices`. Optional v2/v3 credential fields stored encrypted.

## 6. Alerting

### `alert_rules`
- UUID PK. Device and branch FKs align with inventory tables.
- JSONB for channels/recipients to retain flexibility.

### `alert_history`
- UUID PK. `acknowledged_by` captured as UUID (no FK to users due to integer IDs today).
- Indexes on `rule_id` and `device_id` for audit views.

## 7. Discovery & Topology

### `discovery_rules`
- UUID PK with JSONB field for SNMP communities.

### `discovery_results`
- Links to `discovery_rules`. `imported_device_id` optionally references `standalone_devices`.

### `discovery_jobs`
- Tracks job status & stats. `triggered_by_user` stored as UUID (no FK) to match existing schema.

### `discovery_credentials`
- New in Postgres plan to normalize credential storage.
- Index on `credential_type` for quick filtering.

### `network_topology`
- Maintains device-to-device relationships. Indexes on source/target IP.

## 8. Telemetry (Optional Tables)

### `traceroute_results` / `mtr_results`
- Mirrored from SQLite schema for future use.
- `BIGSERIAL` PK ensures growth capacity.

## Open Questions
1. **UUID vs INTEGER FKs**: Several existing SQLAlchemy models use UUID columns pointing to `users.id`. Decide whether to convert users to UUIDs or keep those columns as loose UUID fields.
2. **Branch `device_count`**: Consider replacing with view/materialized view to avoid manual updates.
3. **Historical partitions**: Evaluate table partitioning for `ping_results` and traceroute tables post-migration.
4. **Enum enforcement**: For columns like `role`, `severity`, `monitoring_mode`, introduce Postgres enums once legacy data is cleaned.

## Next Steps
1. Review this plan with backend owners; confirm column type expectations match application models.
2. Finalize DDL (including seed inserts for Georgian geography data) and run through a local PostgreSQL instance.
3. Use the migration validation script (`scripts/verify_postgres_migration.py`) to compare row counts after the first dry run.
4. Update SQLAlchemy models if mismatches are uncovered (e.g., align user UUID usage).

---

Maintained in tandem with the PostgreSQL backlog. Update after schema decisions or migrations.
