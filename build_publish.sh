#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./build_publish.sh build [twine-upload-args...]
  ./build_publish.sh publish [twine-upload-args...]
  ./build_publish.sh test-publish [twine-upload-args...]

Commands:
  build         Build sdist and wheel, then run twine check. This is the default.
  publish       Build, check, then upload to PyPI.
  test-publish  Build, check, then upload to TestPyPI.

Environment:
  PYTHON             Python executable to use for the temporary build venv.
                     Default: first available python3.12, python3.11, python3.10, python3.
  TWINE_API_TOKEN    Optional PyPI API token. If set, the script maps it to
                     TWINE_USERNAME=__token__ and TWINE_PASSWORD.
  TWINE_USERNAME     Optional twine username.
  TWINE_PASSWORD     Optional twine password or API token.

Examples:
  ./build_publish.sh
  TWINE_API_TOKEN=pypi-xxx ./build_publish.sh publish
  TWINE_API_TOKEN=pypi-xxx ./build_publish.sh test-publish --skip-existing
EOF
}

mode="${1:-build}"
case "$mode" in
  build|publish|test-publish)
    if [[ $# -gt 0 ]]; then
      shift
    fi
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown command: $mode" >&2
    usage >&2
    exit 2
    ;;
esac

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_parent="$(dirname "$repo_dir")"
dist_dir="$repo_dir/dist"
python_bin="${PYTHON:-}"
tmp_dir=""

cleanup() {
  if [[ -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 2
  fi
}

if [[ -z "$python_bin" ]]; then
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    then
      python_bin="$candidate"
      break
    fi
  done
fi

if [[ -z "$python_bin" ]]; then
  echo "Python 3.10+ is required, but no suitable interpreter was found." >&2
  echo "Set PYTHON=/path/to/python3.10 and retry." >&2
  exit 2
fi

require_cmd "$python_bin"

echo "==> Repository: $repo_dir"
echo "==> Python: $("$python_bin" --version)"

"$python_bin" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ is required.")
PY

echo "==> Cleaning Python package output"
rm -rf "$dist_dir"
mkdir -p "$dist_dir"

tmp_dir="$(mktemp -d /tmp/somark-py-publish.XXXXXX)"
echo "==> Creating temporary build environment: $tmp_dir/venv"
"$python_bin" -m venv "$tmp_dir/venv"
venv_python="$tmp_dir/venv/bin/python"

echo "==> Installing build tools"
"$venv_python" -m pip install --upgrade pip build twine

echo "==> Building sdist and wheel"
# Run from the parent directory so the repo-local build/ directory cannot shadow
# the PyPA build module.
(
  cd "$repo_parent"
  "$venv_python" -m build "$repo_dir"
)

echo "==> Checking artifacts"
"$venv_python" -m twine check "$dist_dir"/*
ls -lh "$dist_dir"

if [[ "$mode" == "build" ]]; then
  echo "==> Build complete. Publish with: ./build_publish.sh publish"
  exit 0
fi

if [[ -n "${TWINE_API_TOKEN:-}" && -z "${TWINE_PASSWORD:-}" ]]; then
  export TWINE_USERNAME="${TWINE_USERNAME:-__token__}"
  export TWINE_PASSWORD="$TWINE_API_TOKEN"
fi

upload_args=()
if [[ "$mode" == "test-publish" ]]; then
  upload_args+=(--repository testpypi)
  echo "==> Uploading to TestPyPI"
else
  echo "==> Uploading to PyPI"
fi

"$venv_python" -m twine upload "${upload_args[@]}" "$@" "$dist_dir"/*

echo "==> Upload complete"
