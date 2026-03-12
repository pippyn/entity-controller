# AGENTS.md
Repository-specific instructions for coding agents working in `entity-controller`.

## 1) Project Snapshot
- Type: Home Assistant custom integration.
- Main package: `custom_components/entity_controller`.
- Core module: `custom_components/entity_controller/__init__.py`.
- Constants/config keys: `custom_components/entity_controller/const.py`.
- Entity service handlers: `custom_components/entity_controller/entity_services.py`.
- Test suite: `tests/test_*.py` (primary coverage in `tests/test_lightingsm.py`).
- Architecture: event-driven callbacks + finite-state-machine transitions (`transitions` library).

## 2) Rule Files Discovery
- Checked `.cursor/rules/`: not present.
- Checked `.cursorrules`: not present.
- Checked `.github/copilot-instructions.md`: not present.
- No Cursor/Copilot rule files are currently in this repository.
- Treat this file plus repo code/config as the effective rule set.

## 3) Environment Notes
- Dockerfiles use `python:3.6`; keep code compatible with older Python.
- Component test image is based on `homeassistant/home-assistant:dev`.
- Node/npm is used for release/version automation only.
- Test dependencies live in `requirements_test.txt` and `requirements_test_all.txt`.

## 4) Setup Commands
```bash
# local test deps
python -m pip install -r requirements_test.txt

# full HA + pinned tooling deps
python -m pip install -r requirements_test_all.txt
python -m pip install -r requirements_test.txt

# release tooling deps
npm install
```

## 5) Build, Lint, and Test Commands

### Build containers
```bash
docker build -t test_ml .
docker build -f Dockerfile.ci-test -t ec-ci-test .
docker build -f Dockerfile.component -t ec-component-test .
```

### Test (most used)
```bash
# package script (from package.json)
npm test

# equivalent direct command
pytest ./tests/test_lightingsm.py

# all tests under tests/
pytest ./tests
```

### Single-test workflows (important)
```bash
# single test file
pytest ./tests/test_parsing.py

# single test function
pytest ./tests/test_lightingsm.py::test_config_options

# subset by keyword expression
pytest ./tests -k "config_options"
```

### Containerized test runs
```bash
docker run --rm -v ${PWD}:/app test_ml pytest ./tests/test_lightingsm.py
docker compose run --rm component-test-ci pytest
```

### Watch mode (component-style)
```bash
docker compose up -d component-test
docker exec -it component-test /bin/bash
ptw -- -sv
```

### Lint/static analysis status
- No active lint script in `package.json`.
- No current CI lint job in `.github/workflows/master.yml`.
- Historical pinned tools exist in `requirements_test_all.txt`:
  - `flake8==3.6.0`
  - `pylint==2.1.1`
  - `mypy==0.641`
- If linting is requested, run these tools explicitly after installing pinned deps.

## 6) Pytest Defaults and Gotchas
- `pytest.ini` sets `log_cli = true`.
- `pytest.ini` addopts include `--new-first --last-failed -ra -p no:cacheprovider --tb=short --show-capture=no`.
- `python_files` points to `tests/components/test_lightingsm.py` (HA-style path).
- In this repo, explicit test paths are more reliable than implicit discovery.
- For single tests, prefer explicit node ids (`path::test_name`).

## 7) Code Style Guidelines

### Imports
- Preferred grouping (when practical): stdlib, third-party, Home Assistant, local imports.
- Keep imports minimal and remove unused imports in edited files.
- Match nearby style in touched files even if ordering is imperfect.

### Formatting
- Respect `.editorconfig` (`lf` line endings, final newline).
- Preserve existing file style; avoid broad reformat-only diffs.
- Split long conditions/calls into readable multi-line blocks.

### Naming
- Constants/config/service keys use `UPPER_SNAKE_CASE` (`CONF_*`, `SERVICE_*`, etc.).
- Functions and methods use `snake_case`.
- Classes use `CapWords`.
- Tests are named `test_*` in `tests/test_*.py`.
- Legacy camelCase attributes exist (for example `stateEntities`); keep unless a migration is intentional.

### Types and compatibility
- Typing is partial; full type coverage is not required.
- Add type hints for new public helpers when low-friction.
- Keep type syntax Python 3.6 compatible (avoid newer-only typing constructs).

### Async and Home Assistant patterns
- Keep callback signatures and `@callback` usage consistent with nearby code.
- Keep `async_*` naming for async setup/service functions.
- Avoid blocking operations inside async callbacks.
- Preserve event ordering and FSM transition semantics.

### Error handling and logging
- Prefer guard clauses and early returns for invalid state.
- Handle missing HA entities safely: log useful context and continue when possible.
- Catch specific exceptions (commonly `AttributeError`) rather than broad `except`.
- Use context-rich log messages (entity id, old/new state, transition path).

### Config and state-machine changes
- Transition order matters; do not reorder casually.
- Keep config key usage aligned with `const.py`.
- Preserve compatibility for singular/plural config keys (`entity`/`entities`, `sensor`/`sensors`).
- Add targeted tests for behavior changes.

## 8) Testing Expectations for Code Changes
- Small change: run nearest relevant test file.
- FSM logic change: run `tests/test_lightingsm.py` at minimum.
- Parsing/time/config change: run `tests/test_parsing.py`.
- During iteration use single-node tests first, then broader suite before final handoff.

## 9) Release and Versioning
- Release command: `npm run release` (`standard-version -a`).
- `postbump.js` syncs version values into integration metadata files.
- Do not run release tooling unless explicitly requested.

## 10) Scope and Safety for Agents
- Make minimal, targeted edits.
- Do not silently change test infra defaults (`pytest.ini`, Dockerfiles, compose).
- Do not rename widely used config keys unless fully migrated and tested.
- If you add a recurring workflow, document it in this file and/or `README.md`.
