#!/usr/bin/env bash
# Usage: ./scripts/verify.sh
fail=0
chk(){ if curl -fsS "$2" >/dev/null 2>&1; then echo "[PASS] $1"; else echo "[FAIL] $1"; fail=1; fi; }
chk "Status page"   "http://localhost:8000"
chk "Demo app"      "http://localhost:${APP_PORT:-5001}/health"
chk "Grafana"       "http://localhost:${GRAFANA_PORT:-3001}/api/health"
chk "Alertmanager"  "http://localhost:9093/-/ready"
chk "Prometheus"    "http://localhost:9090/-/ready"
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "Some checks failed (wait 1 minute after start and retry)"
