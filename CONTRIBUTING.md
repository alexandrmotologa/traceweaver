# Contributing to TraceWeaver

Thank you for contributing to TraceWeaver. This project welcomes bug fixes, documentation improvements, and performance enhancements.

## Development Setup

Requires Python 3.12 or newer.

```bash
git clone https://github.com/alexandrmotologa/traceweaver.git
cd traceweaver
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Code Quality Standards

Before opening a pull request, verify that all checks pass:

```bash
# Run unit and integration tests
pytest

# Check code formatting and linting
ruff check src tests
ruff format --check src tests
```

To automatically format your code:

```bash
ruff format src tests
ruff check --fix src tests
```

## Pull Request Guidelines

1. Ensure all tests pass.
2. Keep commit messages clear, following the Conventional Commits format (`feat:`, `fix:`, `docs:`, `perf:`).
3. Add unit tests for new analytical or correlation logic.
4. Keep documentation concise and direct, following standard technical writing principles.
