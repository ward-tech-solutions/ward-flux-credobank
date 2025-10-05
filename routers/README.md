# Routers Module

## Purpose
This directory contains modular API routers extracted from the monolithic `main.py` file.

## Structure Plan

```
routers/
├── __init__.py
├── auth.py          # Authentication routes (/api/v1/auth/*)
├── devices.py       # Device management (/api/v1/devices/*)
├── diagnostics.py   # Network diagnostics (/api/v1/diagnostics/*)
├── reports.py       # Reporting endpoints (/api/v1/reports/*)
├── topology.py      # Topology endpoints (/api/v1/topology/*)
└── health.py        # Health checks (/api/v1/health)
```

## Migration Strategy

**Phase 1**: Create router modules (✓ Current step)
**Phase 2**: Extract routes one module at a time
**Phase 3**: Test each module independently
**Phase 4**: Remove extracted code from main.py
**Phase 5**: Update imports and verify all functionality

## Status

- [ ] Phase 1: Setup structure
- [ ] Phase 2: Extract routes
- [ ] Phase 3: Testing
- [ ] Phase 4: Cleanup
- [ ] Phase 5: Verification

## Notes

- All routers use FastAPI's APIRouter
- Each module is self-contained with its dependencies
- No breaking changes to existing functionality
- Gradual migration approach for safety
