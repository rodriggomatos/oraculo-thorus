$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $repoRoot

Write-Host "==> Building apps/mcp-drive..." -ForegroundColor Cyan
docker build -t oraculo-mcp-drive:dev -f apps/mcp-drive/Dockerfile .
if ($LASTEXITCODE -ne 0) { throw "mcp-drive build failed" }

Write-Host "==> Building apps/api..." -ForegroundColor Cyan
docker build -t oraculo-api:dev -f apps/api/Dockerfile .
if ($LASTEXITCODE -ne 0) { throw "api build failed" }

Write-Host "==> Building apps/web..." -ForegroundColor Cyan
docker build -t oraculo-web:dev -f apps/web/Dockerfile .
if ($LASTEXITCODE -ne 0) { throw "web build failed" }

Write-Host "==> All images built successfully" -ForegroundColor Green
docker images | Select-String "oraculo-"
