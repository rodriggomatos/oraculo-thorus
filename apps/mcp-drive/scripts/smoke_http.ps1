# Smoke test do mcp-drive em modo HTTP.
#
# 1. Sobe `python -m mcp_drive` com transport=streamable-http.
# 2. Espera o boot.
# 3. POST /mcp com header correto -> tem que NAO retornar 401.
# 4. POST /mcp sem header -> tem que retornar 401.
# 5. Mata o processo.
#
# Roda independente do .env do repo (env vars setadas no escopo do
# script). NAO toca em .env real.

param(
    [int]$Port = 8765,
    [string]$Token = "smoke-token-$(Get-Random)"
)

$ErrorActionPreference = "Stop"
$mcpDriveDir = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host "==> starting mcp-drive on port $Port (token first 8 chars: $($Token.Substring(0,8))...)"

$env:MCP_DRIVE_TRANSPORT = "streamable-http"
$env:MCP_DRIVE_AUTH_TOKEN = $Token
$env:MCP_DRIVE_HOST = "127.0.0.1"
$env:MCP_DRIVE_PORT = "$Port"

$proc = Start-Process -FilePath "uv" `
    -ArgumentList @("--directory", $mcpDriveDir, "run", "python", "-m", "mcp_drive") `
    -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\mcp-drive-smoke.out" `
    -RedirectStandardError "$env:TEMP\mcp-drive-smoke.err"

try {
    Write-Host "==> waiting for boot (4s)..."
    Start-Sleep -Seconds 4

    $url = "http://127.0.0.1:$Port/mcp"
    $body = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

    Write-Host "==> request WITHOUT token (expect 401)..."
    try {
        $resp = Invoke-WebRequest -Uri $url -Method POST -Body $body `
            -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
        Write-Host "  unexpected status $($resp.StatusCode); FAIL"
        $exit = 1
    } catch [System.Net.WebException] {
        $code = [int]$_.Exception.Response.StatusCode
        if ($code -eq 401) {
            Write-Host "  401 OK"
        } else {
            Write-Host "  got $code; FAIL"; $exit = 1
        }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 401) { Write-Host "  401 OK" } else {
            Write-Host "  $($_.Exception.Message); FAIL"; $exit = 1
        }
    }

    Write-Host "==> request WITH token (expect != 401)..."
    $headers = @{
        "X-MCP-Token" = $Token
        "Accept" = "application/json, text/event-stream"
    }
    try {
        $resp = Invoke-WebRequest -Uri $url -Method POST -Body $body `
            -Headers $headers -ContentType "application/json" `
            -UseBasicParsing -ErrorAction Stop
        Write-Host "  status $($resp.StatusCode) OK (content-type: $($resp.Headers['Content-Type']))"
    } catch [System.Net.WebException] {
        $code = [int]$_.Exception.Response.StatusCode
        if ($code -eq 401) {
            Write-Host "  got 401 with valid token; FAIL"
            $exit = 1
        } else {
            Write-Host "  status $code (acceptable: any non-401 means auth passed)"
        }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -and $code -ne 401) {
            Write-Host "  status $code (auth passed)"
        } else {
            Write-Host "  $($_.Exception.Message); FAIL"
            $exit = 1
        }
    }

    if ($null -eq $exit) { $exit = 0 }
    Write-Host ""
    Write-Host "==> smoke test result: $(if ($exit -eq 0) { 'PASS' } else { 'FAIL' })"
} finally {
    Write-Host "==> killing mcp-drive (PID $($proc.Id))"
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$($proc.Id)" | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

exit $exit
