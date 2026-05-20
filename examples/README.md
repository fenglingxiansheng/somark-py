# somark-py Examples

Standalone Python scripts demonstrating key SDK capabilities.

## Prerequisites

```bash
# From the repo root
pip install -e .
# or: pip install somark

# API key (one of):
export SOMARK_API_KEY=sk-...
# or: somark login
```

## Running Examples

Each example is self-contained and runnable directly:

```bash
cd somark-py

# 01 — Basic sync parse: PDF → markdown
python examples/01_basic_parse.py

# 02 — Multi-format: PDF → md + json in one call
python examples/02_multi_format.py

# 03 — Async task: submit → poll → get result (uses asyncio)
python examples/03_async_task.py

# 07 — PDF to images (local, no API key needed)
python examples/07_pdf_to_images.py

# 08 — Error handling: parse image + catch specific error types
python examples/08_error_handling.py

# 09 — End-to-end pipeline: parse image → save Markdown → preview server
python examples/09_pipeline.py
```

## Scenarios

| File | Scenario | SDK Feature |
|------|----------|-------------|
| `01_basic_parse.py` | Basic sync parse | `parser.parse()` |
| `02_multi_format.py` | Multi-format export | `parser.parse()` with `formats` + `element_formats` |
| `03_async_task.py` | Async task + wait | `AsyncSoMark` + `parser.create()` + `task.wait()` |
| `07_pdf_to_images.py` | PDF → images (local) | `pdf.to_images()` |
| `08_error_handling.py` | Error handling | All error types |
| `09_pipeline.py` | End-to-end pipeline | parse → save Markdown → preview |

## Data Files

```
examples/data/
├── 2010.02399v1.pdf                  — English research paper
├── 5115_Attention_Guided_Alignmen.pdf — English research paper
├── 研报1.png                          — Chinese financial report image
└── 中文试卷-page.png                   — Chinese exam paper image
```

## Notes

- Output files (`output_*.md`, `output_*.json`) are written to `examples/` and not tracked by git.
- Example 07 uses the PDF dependency included with `somark`.
- Example 09 preview server requires the `vendor/somarkdown-viewer` submodule.
- Example 03 uses `AsyncSoMark` with `asyncio.run()` — requires Python 3.7+.
- API key is read from `SOMARK_API_KEY` env var or `~/.somark/config.toml` — never hardcoded.
