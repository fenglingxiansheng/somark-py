# Release Gate

Run this checklist before cutting a Python SDK release, and verify the matching
JavaScript repository with its own `docs/release_gate.md` in the same release
window.

## Repository Hygiene

- Generated package artifacts are local build outputs and should not be
  committed.
- Python bytecode, cache directories, coverage output, virtual environments,
  and package build directories are covered by `.gitignore`.
- Remove tracked generated artifacts with `git rm` only after confirming they
  are tracked. Do not delete unrelated untracked local files during release
  cleanup.
- Confirm the working tree only contains intentional release changes before
  handoff:

```bash
git status --short
git ls-files | grep -E '(__pycache__|\.pyc$)'
```

## Contract Parity

- Keep `docs/sdk_parity_contract.md` equivalent to the JavaScript repository.
- Run the cross-language CLI parity check from the parent coordination
  workspace when it is available.
- Do not change parser, config, task, output, preview, or PDF behavior as part
  of release-gate cleanup.

## Required Checks

```bash
pytest
python -m build
SMOKE_DIR="$(mktemp -d)"
python -m pip install --no-deps --target "$SMOKE_DIR/site" dist/somark-*.whl
PYTHONPATH="$SMOKE_DIR/site" python -c "import somark; from somark.cli.main import app; print(somark.__version__)"
rm -rf "$SMOKE_DIR"
```

If `python -m build` is unavailable, install the local build dependency or
record that the packaging gate could not run because the `build` module is
missing.
