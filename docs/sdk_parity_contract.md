# SoMark SDK Parity Contract

Status: active contract for `somark-py` and `somark-js`.

This document defines language-neutral public behavior for the Python and
JavaScript SDKs. Refactor tasks may change internals, but must preserve this
contract unless a later task explicitly updates this file in both repositories.

The canonical contract is mirrored in each child repository at
`docs/sdk_parity_contract.md`. The files should stay equivalent so either SDK
can be tested and released independently.

## Config

Configuration resolution precedence is:

1. Explicit constructor or function options.
2. Environment variables.
3. `~/.somark/config.toml`.
4. SDK defaults.

Supported config keys are `api_key`, `base_url`, `timeout`, and `max_retries`.
`base_url` values written by config commands must start with `http://` or
`https://`. Config files written by SDK helpers should use private permissions
where the platform supports POSIX file modes.

The shared defaults are:

- `base_url`: `https://somark.tech/api/v1`
- `timeout`: `60`
- `max_retries`: `2`

## Parse Output Formats

Public parse output formats are `md`, `markdown`, `json`, and `zip`.
`md` and `markdown` are aliases for the API format `markdown`. `json` maps to
`json`, and `zip` maps to `zip`.

`smd` and `somarkdown` are not accepted parse output formats. SDKs must reject
unsupported formats before making a parse request and include the valid format
hint `md, markdown, json, zip` in the error message.

## Element Formats

Element formats are optional. Omitted values are not sent to the API.

Supported values are:

- `image`: `url`, `base64`, `file`, `none`
- `formula`: `latex`, `mathml`, `ascii`
- `table`: `markdown`, `html`, `image`
- `cs`: `image`

JavaScript must support `image = "file"` to match Python. If a later service
contract removes this API mode, both SDKs must deprecate it together.

## File Lists

When file-list mode is enabled, the input file is a UTF-8 text manifest with one
path per line. Blank lines are ignored.

Relative paths inside the manifest resolve against the caller's current working
directory, not the manifest file directory. Missing manifests and missing input
files fail before any parse requests are sent.

## Batch Parse

Passing multiple files returns multiple responses or tasks in the same order as
the input list. SDKs must prevalidate that all files exist before sending parse
requests.

Batch parsing may run concurrently. `SOMARK_PARSE_MAX_CONCURRENCY` controls the
limit. Invalid, missing, or values below `1` resolve to `1`. Values above `1`
are allowed but produce a warning because service-side rate limits may apply.

For batch operations, a per-file failure makes the batch operation fail. Later
tasks may add richer partial-failure reporting, but they must update this
contract first.

## Task Lifecycle

Creating an async parse returns a task object with at least `id`, `status`,
`completed`, `warnings`, `refresh`, `wait`, and `result` behavior.

`refresh` polls the async check endpoint and updates the task status and
metadata in place. A successful completed task stores a `ParseResponse`.

`wait` polls until completion or timeout. Timeout raises the SDK timeout error.
Failed tasks raise the SDK parse-failed error. Calling `result` before a
successful completion raises an error.

Task classes may move internally, but public imports documented by each SDK must
remain stable or be kept as compatibility re-exports.

## Warnings

API warnings are collected from the top-level `warnings` array only. Empty,
duplicate, and non-string entries are ignored. Nested or legacy warning shapes
are ignored unless this contract is updated.

Warning text must be attached to response and task objects through their
`warnings` field.

SDK resource/client methods should emit warnings by default using the language's
standard warning mechanism. Model constructors and pure mapping helpers should
not emit warnings after the warning-boundary refactor. CLI code may suppress
warning emission when the user passes the SDK-supported no-warnings option.

Repeated emissions from a single logical API response should be avoided.

## Save Behavior

`ParseResponse.save` supports `md`, `markdown`, `json`, and `zip`.

Saving `md` or `markdown` writes Markdown text. Saving `json` writes the parsed
JSON output. Saving `zip` downloads the ZIP archive referenced by the API ZIP
URL and writes the archive bytes. Saving the ZIP URL as text is not canonical
behavior.

When saving multiple formats, the target path must be an existing directory and
the requested format order is preserved. Saving a single format to a file path
requires the parent directory to already exist. SDK save helpers should not
silently create missing parent directories for file targets.

## Preview

Preview accepts `.md` and `.smd` files. Preview file paths are resolved to an
absolute file path before serving.

The preview server serves vendor assets from `vendor/somarkdown-viewer` and
serves the requested preview file plus sibling assets under the preview file's
directory. Requests that escape the vendor root or preview root are denied.

Missing vendor assets produce an actionable repair hint:
`Run: git submodule update --init --recursive or somark doctor fix`.

## PDF Helpers

PDF-to-image helpers are local utilities and do not require an API key.

Python uses `sopdf`. JavaScript uses `@hyzyla/pdfium` and `pngjs`. These
dependencies are loaded lazily where possible so importing the SDK does not
initialize PDF rendering. Missing optional/runtime PDF dependencies must return
an unsuccessful result with an actionable error string instead of crashing SDK
import.

Default output directory is `./`, default filename format is
`{name}.page-{n}.png`, and default DPI is `150`.

