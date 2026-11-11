#!/usr/bin/env bash
set -e

TARGET_HOST="${1:-localhost}"
echo "Running End-to-End integration test suite against ${TARGET_HOST}..."

python3 "$(dirname "$0")/e2e-test.py" "${TARGET_HOST}"
