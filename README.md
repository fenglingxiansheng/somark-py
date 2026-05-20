# somark-py

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/somark.svg)](https://pypi.org/project/somark/)

The official Python SDK and CLI for [SoMark](https://somark.ai).

This repository is the Python implementation of the shared SoMark SDK + CLI contract. The JavaScript/TypeScript implementation lives in [`somark-js`](https://github.com/SoMarkAI/somark-js). Same product, different runtime.

## Install

```bash
pip install somark
```

## Documentation

Read the official documentation at [docs.somark.tech/documentation](https://docs.somark.tech/open-source-tools).

The docs cover authentication, CLI usage, SDK examples, async tasks, local preview, PDF utilities, API parameters, and error handling. This README stays intentionally short so it does not become a second, worse documentation site.

## Requirements

- Python 3.10+
- A SoMark API key for remote parsing and usage queries
- No API key required for local PDF utilities or SoMarkDown preview
- Docker/Ubuntu PDF rendering may require system libraries: `apt-get install -y --no-install-recommends libxcb1 libgl1 libglib2.0-0`

## License

Apache-2.0
