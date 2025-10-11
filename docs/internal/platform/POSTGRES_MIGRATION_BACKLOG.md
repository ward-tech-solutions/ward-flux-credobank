# PostgreSQL Migration Backlog

Curated issue outlines derived from the latest SQLite audit (2025-10-11). Each entry can be copied into GitHub/Jira with minimal edits.

## 1. Design PostgreSQL Schema with Keys & Constraints
- **Type**: Epic → Task
- **Summary**: Model Ward OPS entities in PostgreSQL with explicit PK/FK and column types.
- **Context**: Tables documented in `docs/internal/platform/DATABASE_AUDIT.md`.
- **Acceptance Criteria**:
  - ERD or schema document covering `standalone_devices`, `branches`, `ping_results`, `alert_rules`, and supporting tables.
  - Defined primary keys (UUID vs. SERIAL) and foreign key relationships.
  - Column type decisions (timestamps with time zone, numeric precision, JSON usage) recorded.
  - Risk assessment for nullable columns & default values included.
- **Dependencies**: None.
- **Deliverables**: Schema proposal doc + DDL migration draft.

## 2. Index Strategy for Telemetry & Lookup Queries
- **Type**: Task
- **Summary**: Specify required indexes to sustain current telemetry scale.
- **Acceptance Criteria**:
  - Index plan for `ping_results` (host/timestamp) and any high-cardinality filters (branch, region).
  - Benchmarks or rationale referencing current row counts (13,179 ping results, 875 devices).
  - Guidance on maintaining indexes post-migration (auto-vacuum, reindex policy).
- **References**: `docs/internal/platform/PING_RESULTS_RETENTION.md`, `migrations/postgres/002_ping_results_indexes.sql`.
- **Dependencies**: Issue 1 (schema finalised).
- **Deliverables**: Index matrix appended to schema doc + SQL statements.

## 3. Telemetry Retention & Archival Policy
- **Type**: Task
- **Summary**: Define how telemetry tables are trimmed/archived in PostgreSQL.
- **Acceptance Criteria**:
  - Retention targets for `ping_results`, future traceroute/MTR tables.
  - Archival workflow (partitioning, cron cleanup, or external storage).
  - Monitoring plan for table growth.
- **Dependencies**: Issues 1 & 2 (schema + indexes).
- **Deliverables**: Policy doc + initial SQL/job scripts.

## 4. Migration Dry-Run Procedure
- **Type**: Task
- **Summary**: Execute migration against a disposable PostgreSQL instance and document results.
- **Acceptance Criteria**:
  - Step-by-step runbook (provision DB, run `migrate_to_postgres.py`, verify row counts).
  - Validation queries comparing SQLite vs PostgreSQL counts for all tables.
  - Rollback/cleanup instructions.
- **Dependencies**: Issues 1–3 completed or draft-ready.
- **Deliverables**: Runbook doc + validation script output.
- **Notes**: Use `scripts/verify_postgres_migration.py` to compare row counts between SQLite and PostgreSQL during dry-runs.

## 5. Legacy SQLite Cleanup
- **Type**: Task
- **Summary**: Remove/deprecate unused SQLite artifacts across environments.
- **Acceptance Criteria**:
  - Confirm `ward_flux.db` and `monitoring.db` deletion is propagated to deployment scripts/backups.
  - Update operational docs referencing old file paths.
  - Optional data archive created (if business requests).
- **Dependencies**: None (already executed in repo; ensure downstream parity).
- **Deliverables**: Checklist completed + confirmation from ops stakeholders.

---

*Maintained by Platform Hardening workstream. Update once issues are created or completed.*
