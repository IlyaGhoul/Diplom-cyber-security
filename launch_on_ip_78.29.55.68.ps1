$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Admin {
    if (Test-IsAdmin) {
        return
    }

    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell -Verb RunAs -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $scriptPath)
    )
    exit
}

function Ensure-FirewallRule {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DisplayName,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $rule = Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue
    if (-not $rule) {
        New-NetFirewallRule -DisplayName $DisplayName -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
    }
}

function Ensure-DockerReady {
    $dockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    $dockerService = Get-Service -Name com.docker.service -ErrorAction SilentlyContinue

    try {
        docker info | Out-Null
        return
    } catch {
    }

    if ($dockerService -and $dockerService.Status -ne "Running") {
        Start-Service -Name com.docker.service
    }

    $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if (-not $dockerProcess -and (Test-Path $dockerDesktopExe)) {
        Start-Process $dockerDesktopExe
    }

    $deadline = (Get-Date).AddMinutes(2)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        try {
            docker info | Out-Null
            return
        } catch {
        }
    }

    throw "Docker daemon did not become ready within 2 minutes."
}

function Get-PublicIp {
    try {
        return (Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 10).ip
    } catch {
        return $null
    }
}

function Wait-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
        }
        Start-Sleep -Seconds 3
    }

    throw "Service did not become ready at $Url within $TimeoutSeconds seconds."
}

function Start-CyberVisStack {
    $composeArgs = @("-f", "compose.yaml", "-f", "compose.caddy.yaml")

    try {
        docker compose @composeArgs up -d --build
        return
    } catch {
        Write-Host "Docker build cache looks unhealthy. Pruning build cache and retrying once..."
        docker builder prune -af | Out-Null
        docker compose @composeArgs up -d --build
    }
}

Ensure-Admin

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path $envPath)) {
    throw ".env not found in $projectRoot"
}

$publicIp = Get-PublicIp

Ensure-DockerReady
Start-CyberVisStack

Ensure-FirewallRule -DisplayName "CyberVis HTTP" -Port 80
Ensure-FirewallRule -DisplayName "CyberVis HTTPS" -Port 443

docker compose -f compose.yaml -f compose.caddy.yaml ps
Wait-HttpReady -Url "http://127.0.0.1:8000/api/stats"

Start-Process "https://api.cybattack.ru/docs"

Write-Host ""
Write-Host "CyberVis production stack is running."
Write-Host "Domain:    api.cybattack.ru"
if ($publicIp) {
    Write-Host "Public IP: $publicIp"
}
Write-Host ""
Write-Host "Open public site: https://api.cybattack.ru/"
Write-Host "Open API docs:    https://api.cybattack.ru/docs"
Write-Host "Open stats JSON:  https://api.cybattack.ru/api/stats"
Write-Host ""
Write-Host "This launcher starts the same HTTPS setup used by GitHub Pages."
