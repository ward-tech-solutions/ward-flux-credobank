# Ward OPS Transformation Roadmap

> Objective: elevate Ward OPS to a premier, production-ready network operations platform with world-class UX, operational resilience, and measurable quality.

## 0. Guiding Principles
- **Ship iteratively**: no massive rewrites. Deliver value in weekly increments with visible wins.
- **Document everything**: every workstream writes its own README + playbook so another engineer (or future assistant) can continue seamlessly.
- **Design tokens first**: UI/UX changes start in the design system before hitting pages.
- **Production grade**: assume zero trust environments, concurrency, and failure modes.
- **Automation or bust**: any manual action repeated twice gets scripted or tested.

## 1. Transformation Workstreams

### A. Platform Hardening
| Epic | Description | Key Deliverables | Dependencies |
| --- | --- | --- | --- |
| Database Migration | Move from SQLite to PostgreSQL (single source of truth) | Alembic migration plan, connection pooling, rollback playbook, data consolidation (eliminate `ward_flux.db`, `monitoring.db`) | Finalise schema mapping |
| Process Supervision | Formalise backend runtime management | systemd/supervisor unit files (or container deploy), health checks, restart policies | Decide hosting environment |
| WebSocket Resilience | Bulletproof live updates | Exponential backoff client reconnect, heartbeat messages, circuit-breaker alerts | Proxy supports `/ws` (already added) |
| Observability Suite | Logging, metrics, tracing | Structured logs (JSON), Prometheus metrics, Grafana dashboards, OpenTelemetry traces, alert thresholds | infra access |
| Security Hardening | Production-grade safeguards | TLS enforcement, rate limiting, dependency scanning, secrets management doc | Choose tooling (e.g., Traefik, Snyk) |

### B. UX Modernisation
| Epic | Description | Key Deliverables |
| --- | --- | --- |
| Design System Unification | Consolidate component styles, states, tokens | Figma/Storybook baseline, Tailwind token map, lint rules for spacing/typography |
| Dashboard & Core Views | Upgrade hero experiences (Dashboard, Monitor, Devices) | Refresh layout, inline drill-ins, global search/command palette |
| Legacy Page Alignment | Bring Discovery, Diagnostics, Reports, Map to new style | Updated cards, dark-mode audit, consistent iconography |
| Accessibility & Internationalisation | Reach WCAG AA, prep for multi-language | Keyboard navigation tests, ARIA labelling, RTL readiness checklist |
| Feedback & Guidance | Improve action transparency | Progress indicators, toast log panel, onboarding walkthrough |

### C. Quality Automation
| Epic | Description | Key Deliverables |
| --- | --- | --- |
| Test Coverage | Expand automated confidence | Vitest + RTL components, backend unit/integration tests, Playwright smoke flows |
| CI/CD Pipeline | Gatekeeper for production readiness | GitHub Actions (or preferred CI) running lint/test/build, artifact publish, changelog |
| Release Engineering | Predictable deployments | Semantic versioning policy, release checklist, canary/blue-green strategy |
| Data Lifecycles | Backup & retention discipline | Automated DB backups, restore drill doc, retention policies for alert history |

## 2. Phase Breakdown

### Phase 1 – Stabilise Foundations (Weeks 1–3)
- Ship PostgreSQL migration plan (document, dry-run script).
- Introduce process supervision (systemd unit file + README).
- Implement WS reconnect with exponential backoff and heartbeat support.
- Kick off structured logging + centralised env config (`.env` templates, secrets doc).
- Draft design system tokens + audit dark mode gaps.

### Phase 2 – UX Excellence & Observability (Weeks 4–6)
- Apply new design system to Dashboard, Devices, Monitor, Alert Rules.
- Align secondary pages and modals with refreshed styles.
- Add command palette & contextual quick actions.
- Deploy Prometheus/Grafana stack, add key metrics (device poll latency, WS uptime).
- Launch Playwright smoke tests & component test suite.

### Phase 3 – Automation & Adoption (Weeks 7–9)
- Finalise PostgreSQL cutover with runbook + rollback.
- Enable CI/CD gating all PRs.
- Build onboarding walkthrough + help overlays.
- Roll out rate limiting, TLS enforcement, API telemetry dashboards.
- Establish release cadence, changelog automation, stakeholder reporting.

## 3. Immediate Next Actions
1. **Compile engineering backlog** – translate epics into GitHub issues (labelled by workstream + phase).
2. **Create design system RFC** – document tokens, typography, component philosophy.
3. **Prototype WS reconnect** – implement client retry with logging + instrumentation.
4. **Audit DB usage** – inventory tables across `ward_ops.db`, `ward_flux.db`, `monitoring.db`.
5. **Set up transformation stand-up doc** – weekly status, blockers, decisions.

## 4. Documentation Expectations
- Every epic gets a `docs/<workstream>/<epic>/README.md` capturing goals, owners, status, links to issues.
- After each chat-assisted session, update `docs/TRANSFORMATION_LOG.md` (template below) to brief future assistants/humans.

```
## YYYY-MM-DD – Session Summary
- Workstream:
- Tasks completed:
- Pending blockers:
- Next recommended moves:
- Files touched:
```

## 5. Success Metrics
- **UX**: SUS score ≥ 85, task completion time improved by 25%.
- **Reliability**: WS uptime ≥ 99.9%, MTTR < 15 min.
- **Quality**: Automated tests cover 80% of critical flows; CI passes < 10 min.
- **Ops**: Zero manual restarts; mean deployment time < 30 min with documented rollback.

## 6. Coordination with Future AI Sessions
- Store active todo list in repo (`docs/TRANSFORMATION_LOG.md`) after each push.
- Reference architecture & roadmap docs before coding.
- Keep responses scoped to current checklist to respect conversation limits.
- When large tasks emerge, create handoff notes for the next assistant to continue seamlessly.

---

This roadmap will evolve; treat it as the living source of truth as we march Ward OPS toward best-in-class status.
