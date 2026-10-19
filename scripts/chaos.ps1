# Usage: .\scripts\chaos.ps1 unhealthy|crash|cpu|memory|recover
param([Parameter(Mandatory=$true)][ValidateSet("unhealthy","crash","cpu","memory","recover")]$Action)
$port = if ($env:APP_PORT) { $env:APP_PORT } else { 5001 }
$base = "http://localhost:$port"
switch ($Action) {
  "unhealthy" { Invoke-RestMethod "$base/chaos/unhealthy" }
  "crash"     { Invoke-RestMethod "$base/chaos/crash" }
  "cpu"       { Invoke-RestMethod "$base/load/cpu?seconds=300" }
  "memory"    { Invoke-RestMethod "$base/load/memory?mb=190" }
  "recover"   { Invoke-RestMethod "$base/chaos/recover"; Invoke-RestMethod "$base/load/release" }
}
