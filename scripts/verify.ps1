# Usage: .\scripts\verify.ps1   (checks that the whole platform is working)
$app = if ($env:APP_PORT) { $env:APP_PORT } else { 5001 }
$graf = if ($env:GRAFANA_PORT) { $env:GRAFANA_PORT } else { 3001 }
$script:fail = 0
function Check($name, [scriptblock]$test) {
  try {
    if (& $test) { Write-Host "[PASS] $name" -ForegroundColor Green }
    else { Write-Host "[FAIL] $name" -ForegroundColor Red; $script:fail++ }
  } catch {
    Write-Host "[FAIL] $name  ($($_.Exception.Message))" -ForegroundColor Red; $script:fail++
  }
}
Check "Status page (port 8000)"        { (Invoke-WebRequest "http://localhost:8000" -UseBasicParsing).StatusCode -eq 200 }
Check "Demo app health (port $app)"    { (Invoke-RestMethod "http://localhost:$app/health").status -eq "ok" }
Check "Grafana (port $graf)"           { (Invoke-RestMethod "http://localhost:$graf/api/health").database -eq "ok" }
Check "Alertmanager ready"             { (Invoke-WebRequest "http://localhost:9093/-/ready" -UseBasicParsing).StatusCode -eq 200 }
Check "Prometheus: all targets UP"     { $t = (Invoke-RestMethod "http://localhost:9090/api/v1/targets").data.activeTargets; ($t.Count -ge 5) -and (@($t | Where-Object { $_.health -ne "up" }).Count -eq 0) }
Check "Prometheus: 6 alert rules loaded" { @((Invoke-RestMethod "http://localhost:9090/api/v1/rules").data.groups.rules).Count -ge 6 }
Check "Container metrics flowing"      { [int]((Invoke-RestMethod "http://localhost:9090/api/v1/query?query=count(cw_container_cpu_percent)").data.result[0].value[1]) -ge 5 }
Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) check(s) failed. If you just started the stack, wait 1 minute and run again." -ForegroundColor Yellow }
