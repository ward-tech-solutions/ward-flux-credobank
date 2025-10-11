# PostgreSQL Cutover Runbook (Draft)

Date: 2025-10-11  
Owner: Platform Hardening Workstream

This runbook defines the end-to-end process for migrating Ward OPS from SQLite (`data/ward_ops.db`) to PostgreSQL. It covers pre-work, execution steps, verification, communication, and rollback. The audience is the on-call engineer plus the migration lead; assume familiarity with Docker and the Ward OPS deployment stack.

Reference docs:
- Schema plan: `docs/internal/platform/POSTGRES_SCHEMA_PLAN.md`
- Migration backlog: `docs/internal/platform/POSTGRES_MIGRATION_BACKLOG.md`
- Verification script: `scripts/verify_postgres_migration.py`
- Migration utility: `migrate_to_postgres.py`

## 1. Timeline & Roles
- **Migration Lead**: Coordinates execution, owns “go/no-go” and rollback decision.
- **Observer**: Runs verification script, confirms dashboards/UI health.
- **Communicator**: Posts status updates to Slack/email distribution.
- **Target window**: 60 min maintenance window with 15 min freeze before start.

## 2. Preconditions (T-1 week)
1. ✅ Complete schema validation on staging using the draft DDL (`migrations/postgres/001_core_schema.sql`).
2. ✅ Ensure all services run successfully on PostgreSQL (`DATABASE_URL`) with `ALLOW_SQLITE_FALLBACK` disabled.
3. ✅ Update infrastructure to provision PostgreSQL (Docker Compose or managed instance). Backups enabled (daily snapshots + WAL archive if available).
4. ✅ Confirm application containers/images read DATABASE_URL from secret store (e.g., Kubernetes secret or `.env`).
5. ✅ Freeze schema changes until migration completes, or version them via Alembic.
6. ✅ Review this runbook with operations and SRE.

## 3. Pre-Migration Checklist (T-1 hour)
- [ ] Announce start/end window to stakeholders (Slack #ops, email). Include contact details.
- [ ] Verify PostgreSQL instance online: `psql $DATABASE_URL -c 'SELECT version();'`.
- [ ] Verify disk space & connection limits: `SELECT pg_size_pretty(pg_database_size('ward_flux'));`.
- [ ] Stop background jobs that write to SQLite (Celery workers, beat) or set application to read-only mode.
- [ ] Take final SQLite backup: `cp data/ward_ops.db data/ward_ops.db.$(date +%Y%m%d-%H%M).bak`.
- [ ] Snapshot Redis (optional) and configuration repos.
- [ ] Confirm `scripts/verify_postgres_migration.py` reachable and Python env has SQLAlchemy installed.
- [ ] Run quick referential sanity check (e.g., ensure `snmp_credentials.device_id` values all exist in `standalone_devices`). Clean or delete orphaned rows prior to migration.

## 4. Dry-Run Procedure (recommended prior day)
1. Start a disposable PostgreSQL instance (docker-compose or `docker run`).
2. Apply schema draft: `psql $DATABASE_URL -f migrations/postgres/001_core_schema.sql`.
3. Run the migration script against a copy of SQLite DB:
   ```bash
   python migrate_to_postgres.py  # uses DATABASE_URL env var
   ```
4. Execute verification script:
   ```bash
   ./venv/bin/python scripts/verify_postgres_migration.py --sqlite path/to/copy.db --postgres $DATABASE_URL --fail-on-mismatch
   ```
5. Record deltas and adjust migration script/schema before production run.

## 5. Production Migration Steps (T-0)
1. **Quiesce writes**
   - Stop API workers (`systemctl stop ward-api` or `docker compose stop api celery-worker celery-beat`).
   - Confirm no processes hold a write lock on SQLite: `lsof data/ward_ops.db`.
2. **Backup confirmation**
   - Ensure the latest `.bak` file is present and accessible on a separate disk.
3. **Provision PostgreSQL schema**
   - `psql $DATABASE_URL -f migrations/postgres/001_core_schema.sql`.
   - Apply reference data (Georgian regions/cities) if not handled by migration script.
   - Run incremental SQL migrations via `scripts/run_sql_migrations.py` (records applied migrations in `schema_migrations`).
4. **Run migration**
   ```bash
   python migrate_to_postgres.py
   ```
   - Respond “yes” when prompted.
   - Monitor output for table counts/errors.
5. **Verify counts**
   ```bash
   ./scripts/verify_postgres_migration.py --fail-on-mismatch
   ```
   - Investigate any differences before proceeding.
6. **Smoke tests (database)**
   - `psql $DATABASE_URL -c 'SELECT COUNT(*) FROM standalone_devices;'`
   - Run targeted queries for high-volume tables (`ping_results`, `alert_rules`).
7. **Start services on PostgreSQL**
   - Update environment (`DATABASE_URL`) if not already pointing to PostgreSQL.
   - Start API/Celery/worker processes.
8. **Application smoke tests**
   - Hit `/api/v1/health` endpoint.
   - Load the UI dashboard/monitor page; confirm counts match expected.
   - Trigger sample background job (e.g., ping device) to confirm writes succeed.
9. **Announce completion**
   - Communicator posts to Slack/email with success message and next verification window.

## 6. Post-Migration Monitoring (T+1 hour)
- Monitor application logs for SQL errors or connection issues.
- Validate scheduled tasks (Celery beat) resume without errors.
- Ensure backups begin running against PostgreSQL (confirm first snapshot).
- Archive SQLite backup for retention window (e.g., 30 days).
- Optional: run `scripts/celery_smoke_test.py` against a staging database to confirm alert evaluation & retention tasks succeed.

## 7. Rollback Strategy

### Triggers for rollback
- Migration script fails or produces mismatched counts that cannot be resolved quickly.
- Application smoke tests fail (API errors, UI data missing).
- PostgreSQL availability issues (instance unresponsive, resource exhaustion).

### Rollback steps
1. **Stop services** currently pointed at PostgreSQL.
2. **Restore SQLite**
   - Replace `data/ward_ops.db` with latest backup: `cp data/ward_ops.db.YYYYMMDD-HHMM.bak data/ward_ops.db`.
3. **Revert configuration**
   - Set `DATABASE_URL=sqlite:///...` and `ALLOW_SQLITE_FALLBACK=true` (temporary).
4. **Start services** against SQLite.
5. **Verify** health endpoints/UI.
6. **Document incident** in runbook & transformation log; plan follow-up fix before reattempt.

### Post-rollback actions
- Investigate root cause, capture logs.
- Verify PostgreSQL data is dropped or snapped for forensic inspection.
- Schedule new migration window only after issue resolved.

## 8. Communication Templates

**Start notice (T-1 hour)**
```
Heads up: Ward OPS database migration to PostgreSQL begins at <time>. Expect up to 60 min of read-only mode. Monitoring/alerts may be delayed. Contact <lead> for urgent issues.
```

**Completion notice**
```
Migration complete. Ward OPS now running on PostgreSQL. Please report anomalies in #ops. We will monitor closely for the next hour.
```

**Rollback notice**
```
Migration rolled back at <time>. Systems are back on SQLite. Post-mortem to follow; expect reschedule.
```

## 9. Outstanding Tasks
- Populate Alembic migrations or equivalent automation before production run.
- Decide on PostgreSQL user/role permissions (read-only reporting role, etc.).
- Automate scripts within CI/CD pipeline post-cutover (type checks, verification).

---

Maintain this document as procedures evolve. Update after the first dry-run and production cutover.
