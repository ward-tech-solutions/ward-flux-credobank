# Contributing to WARD Tech Solutions

## Development Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Pre-commit Hooks (RECOMMENDED)
```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Code Quality Tools

### Auto-formatting with Black
```bash
# Format all Python files
black .

# Check what would be changed (dry-run)
black --check .
```

### Import Sorting with isort
```bash
# Sort all imports
isort .

# Check only (don't modify)
isort --check-only .
```

### Linting with Ruff
```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Security Scanning with Bandit
```bash
# Scan for security issues
bandit -r . -c pyproject.toml
```

### Type Checking with MyPy
```bash
# Check types
mypy main.py
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

## API Documentation

After starting the server, access:
- **Swagger UI**: http://localhost:5001/docs
- **ReDoc**: http://localhost:5001/redoc
- **OpenAPI JSON**: http://localhost:5001/openapi.json

## Development Workflow

1. **Create a branch** for your feature
2. **Make changes** to the code
3. **Run formatters**: `black .` and `isort .`
4. **Run linter**: `ruff check --fix .`
5. **Run tests**: `pytest`
6. **Commit changes** (pre-commit hooks will run automatically)
7. **Push and create PR**

## Code Style Guidelines

- **Line length**: 100 characters (enforced by Black)
- **Import order**: stdlib → third-party → first-party (enforced by isort)
- **Type hints**: Encouraged but not required
- **Docstrings**: Required for public functions and classes

## Pre-commit Hooks

The following checks run automatically on `git commit`:
- ✅ Black code formatting
- ✅ isort import sorting
- ✅ Ruff linting with auto-fix
- ✅ Bandit security checks
- ✅ Trailing whitespace removal
- ✅ End-of-file fixing
- ✅ YAML/JSON/TOML validation
- ✅ Large file detection
- ✅ Private key detection

## Troubleshooting

### Pre-commit hooks fail
```bash
# Run hooks manually to see details
pre-commit run --all-files

# Skip hooks temporarily (NOT RECOMMENDED)
git commit --no-verify
```

### Code formatting conflicts
```bash
# Let Black handle it
black .
isort .
```

## Questions?

Contact: info@wardops.tech
