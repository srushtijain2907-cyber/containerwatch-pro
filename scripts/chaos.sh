#!/usr/bin/env bash
# Usage: ./scripts/chaos.sh unhealthy|crash|cpu|memory|recover
BASE=${BASE:-http://localhost:${APP_PORT:-5001}}
case "$1" in
  unhealthy) curl -s "$BASE/chaos/unhealthy" ;;
  crash)     curl -s "$BASE/chaos/crash" ;;
  cpu)       curl -s "$BASE/load/cpu?seconds=300" ;;
  memory)    curl -s "$BASE/load/memory?mb=190" ;;
  recover)   curl -s "$BASE/chaos/recover"; curl -s "$BASE/load/release" ;;
  *) echo "Usage: $0 unhealthy|crash|cpu|memory|recover"; exit 1 ;;
esac
echo
