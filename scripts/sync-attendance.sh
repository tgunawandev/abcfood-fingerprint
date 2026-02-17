#!/bin/bash
# Attendance sync wrapper
# Fetches attendance from all devices and outputs in Odoo-compatible format

set -e

TODAY=$(date +%Y-%m-%d)

echo "=== Syncing attendance for $TODAY ==="

fingerprint-ctl attendance get tmi --from "$TODAY"
fingerprint-ctl attendance get outsourcing --from "$TODAY"

echo "=== Done ==="
