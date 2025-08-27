# Branch Protection Setup

To ensure code quality and prevent breaking changes, configure branch protection rules for the `master` branch:

## Setup Instructions

1. Go to your repository settings: https://github.com/HromekFr/statshunter-optimizer/settings

2. Navigate to **Branches** in the left sidebar

3. Click **Add rule** or edit existing rule for `master` branch

4. Configure the following settings:

### Required Settings

- [x] **Require a pull request before merging**
  - [x] Require approvals: 1 (optional, or set to 0 for solo projects)
  - [x] Dismiss stale pull request approvals when new commits are pushed
  
- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - Add these status checks:
    - `test (3.12)` - Main Python version test
    - `test (3.11)` - Compatibility test
    - `integration-test` - Integration tests
  
- [x] **Require conversation resolution before merging**

- [x] **Include administrators** (optional, recommended for consistency)

### Optional Settings

- [ ] **Require signed commits** (if using GPG signing)
- [ ] **Require linear history** (if preferring rebases over merge commits)
- [ ] **Restrict who can push to matching branches** (for team projects)

## GitHub Actions Status

The following GitHub Actions workflows will run automatically:

1. **On every push**: Unit tests, linting, type checking
2. **On pull requests**: Full test suite with coverage reporting
3. **Matrix testing**: Python 3.9, 3.10, 3.11, and 3.12

## Test Requirements

All pull requests must pass:
- ✅ Unit tests for routing services
- ✅ API endpoint tests
- ✅ Integration tests
- ✅ Code linting (flake8)
- ✅ Optional: Type checking (mypy)

## Verifying Setup

After configuration, your pull request page should show:
- Status checks pending/running when PR is created
- Green checkmarks when all tests pass
- Merge button enabled only when all checks pass

## Manual Testing

Run tests locally before pushing:
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m unittest tests.test_routing_services -v

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=html
```