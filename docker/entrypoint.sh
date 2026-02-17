#!/bin/bash
set -e

echo "=== ABCFood Fingerprint Service ==="
echo "Environment: ${ENVIRONMENT:-production}"
echo "=================================="

exec fingerprint-ctl "$@"
