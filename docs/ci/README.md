# PEG CI/CD - Enterprise Grade

This document describes the CI/CD pipeline configuration for the PEG project.

## Features

- **Parallel Matrix Testing**: Tests run on Python 3.11 and 3.12 simultaneously
- **Pip + Python Caching**: 2-3x faster builds with dependency caching
- **80%+ Coverage Enforced**: Tests fail if coverage drops below threshold
- **Security Scanning**: Bandit static analysis + Safety dependency checks
- **Auto-Deploy Preview**: Automatic deployment on main branch merges
- **Zero-Downtime Ready**: Pipeline designed for production deployments

## Pipeline Structure

```
test (matrix: 3.11, 3.12)
         │
         ▼
      security
         │
         ▼
   deploy-preview (main only)
```

## Running Locally

### Full Test Suite with Coverage
```bash
pytest -n auto --cov=src --cov-fail-under=80
```

### Security Scan
```bash
pip install bandit safety
bandit -r src
safety check
```

## Configuration Files

- `.github/workflows/ci.yml` - Main CI pipeline
- `pyproject.toml` - Project configuration including dev dependencies

## Workflow Triggers

- **Push to main**: Full pipeline including deploy-preview
- **Pull requests**: Test and security jobs only (no deploy)

## Coverage Requirements

The pipeline enforces a minimum 80% code coverage. If coverage drops below this threshold, the CI will fail.

## Security Checks

1. **Bandit**: Static security analysis for Python code
2. **Safety**: Checks dependencies for known vulnerabilities

Security scan results are uploaded as artifacts for review.
