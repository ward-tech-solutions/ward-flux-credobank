# WebSocket Resilience Plan

**Scope**: `/ws/updates` endpoint powering Monitor real-time updates.  
**Owner**: Platform Hardening Workstream  
**Status**: Draft (implementation pending)

## 1. Current Behaviour
- Client opens WS to `ws://<host>/ws/updates` (proxied via Vite dev server).
- If connection drops, browser auto-close triggers `onclose`, component schedules reconnect with fixed 5s delay (no jitter or max retries).
- No heartbeat/ping messages; server relies on TCP keepalive.
- Errors only logged to console; UI does not alert users about stale data.

## 2. Target Enhancements
1. **Heartbeat Protocol**
   - Server sends `{"type":"heartbeat"}` every 30s.
   - Client responds with `{"type":"pong"}` OR measures drift to detect latency.
   - If heartbeat missed twice → trigger reconnect.
2. **Exponential Backoff Reconnect**
   - Base delay 2s; backoff factor 1.5; jitter ±0.5s; cap at 60s.
   - Reset delay after stable connection (≥2 minutes).
3. **Offline UX Feedback**
   - Display inline banner (“Live updates paused, attempting to reconnect…”) with retry countdown.
   - Greyscale live metrics or show “stale” badge on cards.
4. **Instrumentation**
   - Log connection lifecycle with structured payloads (ready for aggregated metrics).
   - Expose Prometheus counter `ws_updates_disconnections_total` and gauge `ws_updates_clients`.
   - Client logs send to monitoring endpoint (optional) for aggregated telemetry.
5. **Server Safeguards**
   - Limit handshake rate (rate limit + auth validation).
   - Implement idle timeout (e.g., close client after 10 min of no heartbeat).
   - Wrap broadcast loop with circuit breaker to avoid cascading failures.
6. **Testing**
   - Automated Playwright test simulating disconnect & reconnect.
   - Unit tests for backoff scheduler (pure function verifying delays).
   - Chaos monkey script (CLI) toggling network to validate UX banner.

## 3. Implementation Steps
1. Backend (`main.py` / `routers/websockets.py`)
   - Add heartbeat scheduler (async loop) + pong handling.
   - Track client metadata (last heartbeat time) and drop stale clients.
   - Emit metrics via Prometheus / StatsD (expose endpoint `/metrics` if not already).
2. Frontend (`Monitor.tsx`)
   - Abstract WebSocket manager into hook `useResilientWebSocket`.
   - Implement exponential backoff with jitter (store state in ref).
   - Surface connection state to UI (banner + stale indicator).
   - Log events to `console.info` (dev) and optional remote logger (prod).
3. Configuration
   - Make heartbeat interval and retry config adjustable via env (both FE and BE).
   - Document defaults in `.env.example`.
4. QA
   - Manual test plan: disconnect server, throttle network, simulate tab sleep.
   - Add Playwright scenario verifying banner + auto-recovery.

## 4. Timeline
| Week | Milestone |
| --- | --- |
| Week 1 | Backend heartbeat + metrics |
| Week 2 | Frontend resilient hook + UX banner |
| Week 3 | Automated tests + chaos verification |
| Week 4 | Launch, monitor metrics, tweak thresholds |

## 5. Risks & Mitigations
- **Risk**: Frequent reconnect loops overwhelm backend.  
  **Mitigation**: Cap retries, implement server-side rate limiting, share metrics.
- **Risk**: Banner fatigue if transient flaps.  
  **Mitigation**: Debounce notifications, only show if downtime > 5s.
- **Risk**: Mobile devices sleeping background tabs.  
  **Mitigation**: Resume handshake automatically and mark data stale while asleep.

## 6. Open Questions
- Should we fallback to polling after N failed attempts?
- Do we need auth token refresh tied to WebSocket handshake?
- How will metrics integrate with existing observability stack (Prometheus vs. Loki etc.)?

## 7. Next Actions
1. Create GitHub issues (backend heartbeat, frontend hook, UX banner, tests).
2. Align with observability plan to expose metrics endpoint.
3. Draft UX mock for offline banner (design review).

---

*Update document as implementation progresses; link PRs + metrics dashboards once available.*
