# Contributing

## Setup

```bash
git clone https://github.com/waydroid-toolkit/waydroid-toolkit
cd waydroid-toolkit
pip install -e ".[dev]"
```

## Running tests

```bash
# Unit tests only (no Waydroid required)
pytest tests/unit/

# Integration tests (requires live Waydroid session)
pytest tests/integration/

# All tests, skip integration
pytest -m "not integration"
```

## Code style

```bash
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

## Adding a new module

1. Create `src/waydroid_toolkit/modules/<name>/`.
2. Add `__init__.py` with public exports.
3. Register any CLI commands in `src/waydroid_toolkit/cli/commands/` and
   wire them into `cli/main.py`.
4. Add unit tests in `tests/unit/test_<name>.py`.
5. Add integration tests in `tests/integration/test_<name>_integration.py`.
6. Document in `docs/modules/<name>.md` and `docs/cli/<name>.md`.

## Adding a new extension

See [Extensions module](../modules/extensions.md#adding-a-new-extension).

## Commit style

Follow the existing commit messages: short imperative subject, no period.
Co-author line: `Co-authored-by: Ona <no-reply@ona.com>`.
