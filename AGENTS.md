# somark-py Agent Guide

## Project Boundary

This repository contains the Python implementation of the SoMark SDK and `somark` CLI. It is developed in parallel with the JavaScript/TypeScript implementation, but it is its own package and release unit.

Keep behavior aligned with `somark-js` wherever the public CLI or SDK capability is intended to be shared. Language-specific naming is fine; surprise behavior is not.

When work is initiated from the parent `somark-cli` workspace, always consider the matching `somark-js` repository before finishing. Public CLI and SDK behavior changes usually require synchronized changes in both repositories. If no JavaScript change is needed, verify that explicitly rather than assuming it.

## What Must Stay Aligned

- Parse endpoints: `/parse/sync`, `/parse/async`, `/parse/async_check`
- Usage endpoint: `/usage`
- Parse request fields: `output_formats`, `element_formats`, `feature_config`
- CLI command shape, exit codes, and local-tool behavior
- Error categories exposed to users

## Useful Commands

```bash
uv run pytest
uv run somark --help
uv run somark parse --help
```

After changes, run the relevant Python tests in this repository and commit the Python changes here separately from any `somark-js` commit.

## Maintenance Rules

- Keep README short. Product usage belongs in the official docs at `https://docs.somark.tech/documentation`.
- Do not duplicate long API tables in README or agent files.
- Prefer small compatibility fixes over language-specific surprises.
- Local PDF and preview features must not require an API key.
- Remote parse and usage features must fail clearly when the API key is missing.
- Prefer explicit validation errors over silently dropping unsupported parameters.
