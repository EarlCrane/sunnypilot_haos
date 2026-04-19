# Repository Guidelines

## Project Structure & Module Organization
This repository is a Home Assistant custom integration packaged under `custom_components/sunnypilot/`. Core setup lives in `__init__.py`, cloud polling in `coordinator.py`, API access in `client.py`, and entity platforms in `switch.py`, `select.py`, and `number.py`. Shared metadata and the parameter registry live in `const.py`. User-facing strings belong in `strings.json` and `translations/en.json`. Repository-level support files include `README.md`, `hacs.json`, `lovelace_dashboard.yaml`, and the standalone helper `sunnylink_client.py`.

## Build, Test, and Development Commands
There is no separate build step. Use lightweight validation commands from the repo root:

```bash
python3 sunnylink_client.py --help
python3 -m compileall -q custom_components/sunnypilot sunnylink_client.py
python3 sunnylink_client.py devices --refresh-token "$SUNNYLINK_REFRESH_TOKEN"
```

The first confirms the helper CLI still parses, the second catches syntax errors, and the third is useful when debugging Sunnylink connectivity outside Home Assistant. For end-to-end testing, copy `custom_components/sunnypilot/` into your HA config, restart Home Assistant, and add or reload the integration from Settings.

## Coding Style & Naming Conventions
Follow existing Home Assistant patterns: 4-space indentation, type hints, concise docstrings, and `async_` prefixes for HA entrypoints. Keep blocking network work inside executor-backed sync helpers rather than inside entity methods. Preserve the current module split by platform. Use descriptive constant names in `UPPER_SNAKE_CASE`, config keys in lower snake case, and align new parameter definitions with the existing `PARAM_REGISTRY` shape in `const.py`.

## Testing Guidelines
No automated test suite is checked in today, so every change needs manual validation. At minimum, verify setup, re-auth, device selection, and one write path for each affected entity type (`switch`, `number`, `select`). Confirm updated state returns after the 15-second coordinator poll. If you change strings or dashboard YAML, verify them in the Home Assistant UI.

## Commit & Pull Request Guidelines
Recent history mixes good release-style subjects with vague messages. Prefer short imperative subjects such as `Add reauth retry logging` or `Fix select option coercion`. PRs should describe the behavior change, list manual validation steps, note the Home Assistant version used, and include screenshots only for UI or dashboard changes.

## Security & Configuration Tips
Never commit refresh tokens, device IDs, or captured API payloads. Keep secrets in Home Assistant config entries or local environment variables when using `sunnylink_client.py`.
