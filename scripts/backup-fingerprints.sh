#!/bin/bash
# Cron-friendly backup wrapper
# Usage: ./backup-fingerprints.sh [device]
# Default: backs up all devices

set -e

DEVICE=${1:-""}

if [ -n "$DEVICE" ]; then
    fingerprint-ctl backup run "$DEVICE"
else
    fingerprint-ctl backup run tmi
    fingerprint-ctl backup run outsourcing
fi
