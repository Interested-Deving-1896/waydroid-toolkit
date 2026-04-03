# Contributing to waydroid-toolkit

## Development setup

```bash
git clone https://github.com/waydroid-toolkit/waydroid-toolkit
cd waydroid-toolkit
pip install -e ".[dev]"
```

## Running tests

```bash
# Unit tests only (no Waydroid required)
pytest tests/unit

# All tests including integration (requires a live Waydroid session)
pytest
```

## Code style

```bash
ruff check src tests
ruff format src tests
mypy src
```

CI enforces ruff and mypy on every PR.

## Adding a new CLI command

1. Create `src/waydroid_toolkit/cli/commands/<name>.py` with a `cmd` Click group or command.
2. Register it in `src/waydroid_toolkit/cli/main.py`.
3. Add unit tests in `tests/unit/test_<name>.py`.
4. Add a doc page in `docs/cli/<name>.md` and link it from `mkdocs.yml`.

## Adding a new module

1. Create `src/waydroid_toolkit/modules/<name>/` with `__init__.py` and implementation.
2. Wire the module into the relevant CLI command.
3. Add unit tests.

## Commit messages

Follow the existing style: `type: short description` (e.g. `feat: add wdt stream start`).
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

## Pull requests

- Target `main`.
- Keep PRs focused — one feature or fix per PR.
- All CI checks must pass before merge.
- Add a changelog entry in `CHANGELOG.md` under `[Unreleased]`.

## Security

Report security issues privately via GitHub Security Advisories, not as public issues.

## License

By contributing, you agree your changes are licensed under GPL-3.0 (see `LICENSE`).
