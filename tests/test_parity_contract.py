from pathlib import Path


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "docs" / "sdk_parity_contract.md"


def test_sdk_parity_contract_covers_required_topics():
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    required_headings = [
        "## Config",
        "## Parse Output Formats",
        "## Element Formats",
        "## File Lists",
        "## Batch Parse",
        "## Task Lifecycle",
        "## Warnings",
        "## Save Behavior",
        "## Preview",
        "## PDF Helpers",
    ]
    for heading in required_headings:
        assert heading in contract


def test_sdk_parity_contract_records_decided_public_values():
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "`md`, `markdown`, `json`, and `zip`" in contract
    assert "`image`: `url`, `base64`, `file`, `none`" in contract
    assert "`smd` and `somarkdown` are not accepted parse output formats" in contract
    assert "SDKs must prevalidate that all files exist before sending parse" in contract
    assert "`SOMARK_PARSE_MAX_CONCURRENCY` controls the" in contract
    assert "API warnings are collected from the top-level `warnings` array only" in contract
    assert "Saving `zip` downloads the ZIP archive" in contract
    assert "SDK save helpers should not\nsilently create missing parent directories" in contract
    assert "Relative paths inside the manifest resolve against the caller's current working" in contract
    assert "Requests that escape the vendor root or preview root are denied" in contract
    assert "Missing optional/runtime PDF dependencies must return\nan unsuccessful result" in contract


def test_release_gate_documents_final_verification_commands():
    release_gate = (CONTRACT_PATH.parent / "release_gate.md").read_text(encoding="utf-8")
    assert "Generated package artifacts are local build outputs and should not be\n  committed" in release_gate
    assert "Do not delete unrelated untracked local files" in release_gate
    assert "pytest" in release_gate
    assert "python -m build" in release_gate
    assert 'python -m pip install --no-deps --target "$SMOKE_DIR/site" dist/somark-*.whl' in release_gate
    assert 'PYTHONPATH="$SMOKE_DIR/site" python -c "import somark; from somark.cli.main import app; print(somark.__version__)"' in release_gate
