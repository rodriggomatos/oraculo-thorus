#Requires -Version 5.1

$ErrorActionPreference = "Stop"

$apiRoot = Split-Path $PSScriptRoot -Parent
$appsRoot = Split-Path $apiRoot -Parent
$aiSrc = Join-Path $appsRoot "ai\src"
$apiSrc = Join-Path $apiRoot "src"

Write-Host "==> Killing processes listening on port 8000..."
$conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($c in $conns) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Write-Host "    killed PID $($c.OwningProcess)"
        } catch {
            Write-Host "    failed to kill PID $($c.OwningProcess): $_"
        }
    }
} else {
    Write-Host "    (none found)"
}

Write-Host "==> Clearing __pycache__ recursively..."
$caches = @(
    Get-ChildItem -Path $apiSrc, $aiSrc -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
)
foreach ($c in $caches) {
    Remove-Item -Recurse -Force $c.FullName -ErrorAction SilentlyContinue
}
Write-Host "    cleared $($caches.Count) directories"

Set-Location $apiRoot
Write-Host "==> Starting uvicorn (reload watches apps/api/src and apps/ai/src)..."
& uv run uvicorn oraculo_api.main:app `
    --port 8000 `
    --reload `
    --reload-dir $apiSrc `
    --reload-dir $aiSrc
