$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Update-EnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $content = ""
    if (Test-Path $Path) {
        $content = Get-Content $Path -Raw
    }

    $escapedName = [regex]::Escape($Name)
    if ($content -match "(?m)^$escapedName=") {
        $content = [regex]::Replace($content, "(?m)^$escapedName=.*$", "$Name=$Value")
    } else {
        if ($content -and -not $content.EndsWith("`r`n")) {
            $content += "`r`n"
        }
        $content += "$Name=$Value`r`n"
    }

    Set-Content -Path $Path -Value $content -Encoding ASCII
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
        try {
            Start-Service -Name com.docker.service
        } catch {
        }
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

function Wait-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 90
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

function Get-CloudflaredPath {
    $candidates = @(
        (Join-Path $projectRoot ".tools\cloudflared.exe"),
        "C:\Program Files\cloudflared\cloudflared.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "cloudflared.exe not found. Expected it in .tools or Program Files."
}

function Ensure-CloudflareLogin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CloudflaredPath,
        [Parameter(Mandatory = $true)]
        [string]$CertPath
    )

    if (Test-Path $CertPath) {
        return
    }

    Write-Host ""
    Write-Host "Cloudflare login is required once."
    Write-Host "A browser window should open now. Select the zone for cybattack.ru and approve access."
    Write-Host ""

    & $CloudflaredPath tunnel login

    if (-not (Test-Path $CertPath)) {
        throw "Cloudflare login did not finish. cert.pem was not created."
    }
}

function Get-TunnelInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CloudflaredPath,
        [Parameter(Mandatory = $true)]
        [string]$TunnelName
    )

    $raw = & $CloudflaredPath tunnel list -o json --name $TunnelName
    if (-not $raw) {
        return $null
    }

    $items = $raw | ConvertFrom-Json
    if ($items -is [System.Array]) {
        if ($items.Count -gt 0) {
            return $items[0]
        }
        return $null
    }

    return $items
}

function Ensure-Tunnel {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CloudflaredPath,
        [Parameter(Mandatory = $true)]
        [string]$TunnelName
    )

    $tunnel = Get-TunnelInfo -CloudflaredPath $CloudflaredPath -TunnelName $TunnelName
    if ($tunnel) {
        return $tunnel
    }

    Write-Host "Creating Cloudflare Tunnel '$TunnelName'..."
    & $CloudflaredPath tunnel create $TunnelName | Out-Host

    $tunnel = Get-TunnelInfo -CloudflaredPath $CloudflaredPath -TunnelName $TunnelName
    if (-not $tunnel) {
        throw "Tunnel '$TunnelName' was not found after creation."
    }

    return $tunnel
}

function Write-TunnelConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath,
        [Parameter(Mandatory = $true)]
        [string]$TunnelId,
        [Parameter(Mandatory = $true)]
        [string]$CredentialsPath,
        [Parameter(Mandatory = $true)]
        [string]$Hostname
    )

    $yaml = @(
        "tunnel: $TunnelId"
        "credentials-file: $CredentialsPath"
        ""
        "ingress:"
        "  - hostname: $Hostname"
        "    service: http://localhost:80"
        "  - service: http_status:404"
        ""
    ) -join "`r`n"

    Set-Content -Path $ConfigPath -Value $yaml -Encoding ASCII
}

function Ensure-DnsRoute {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CloudflaredPath,
        [Parameter(Mandatory = $true)]
        [string]$TunnelName,
        [Parameter(Mandatory = $true)]
        [string]$Hostname
    )

    Write-Host "Routing DNS $Hostname to tunnel $TunnelName..."
    & $CloudflaredPath tunnel route dns -f $TunnelName $Hostname | Out-Host
}

function Stop-ExistingCloudflared {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MatchText
    )

    $processes = Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        if ($proc.CommandLine -and $proc.CommandLine -like "*$MatchText*") {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-NamedTunnel {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CloudflaredPath,
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [Parameter(Mandatory = $true)]
        [string]$PidPath
    )

    if (Test-Path $LogPath) {
        Remove-Item $LogPath -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $PidPath) {
        Remove-Item $PidPath -Force -ErrorAction SilentlyContinue
    }

    Stop-ExistingCloudflared -MatchText $ConfigPath

    Start-Process -FilePath $CloudflaredPath `
        -ArgumentList @(
            "tunnel",
            "--config", $ConfigPath,
            "--pidfile", $PidPath,
            "--logfile", $LogPath,
            "--loglevel", "info",
            "--edge-ip-version", "4",
            "run"
        ) `
        -PassThru | Out-Null
}

function Wait-TunnelProcessReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PidPath,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $PidPath) {
            $pidValue = (Get-Content $PidPath -ErrorAction SilentlyContinue | Select-Object -First 1)
            if ($pidValue) {
                return
            }
        }

        if (Test-Path $LogPath) {
            $tail = Get-Content $LogPath -Tail 20 -ErrorAction SilentlyContinue
            if (($tail -join " ") -match "failed|error") {
                throw "cloudflared failed to start. Check $LogPath"
            }
        }

        Start-Sleep -Seconds 2
    }

    throw "cloudflared did not become ready within $TimeoutSeconds seconds."
}

function Wait-PublicApiReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
            if ($response.StatusCode -eq 200) {
                return $response.Content
            }
        } catch {
        }

        Start-Sleep -Seconds 5
    }

    if (Test-Path $LogPath) {
        $tail = Get-Content $LogPath -Tail 40 -ErrorAction SilentlyContinue
        if ($tail) {
            Write-Host ""
            Write-Host "cloudflared log tail:"
            $tail | ForEach-Object { Write-Host $_ }
            Write-Host ""
        }
    }

    throw "Public API did not become ready at $Url within $TimeoutSeconds seconds."
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$toolsDir = Join-Path $projectRoot ".tools"
Ensure-Directory -Path $toolsDir

$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path $envPath)) {
    throw ".env not found in $projectRoot"
}

$hostname = "api.cybattack.ru"
$tunnelName = "cyber-vis-api"
$cloudflareDir = Join-Path $env:USERPROFILE ".cloudflared"
$certPath = Join-Path $cloudflareDir "cert.pem"
$configPath = Join-Path $toolsDir "cloudflared-config.yml"
$logPath = Join-Path $toolsDir "cloudflared-named.log"
$pidPath = Join-Path $toolsDir "cloudflared-named.pid"

Ensure-Directory -Path $cloudflareDir
Update-EnvValue -Path $envPath -Name "CYBER_VIS_DOMAIN" -Value $hostname
Update-EnvValue -Path $envPath -Name "CYBER_VIS_API_BASE" -Value "https://$hostname/"

Ensure-DockerReady
Start-CyberVisStack
Wait-HttpReady -Url "http://127.0.0.1:8000/api/stats"

$cloudflared = Get-CloudflaredPath
Ensure-CloudflareLogin -CloudflaredPath $cloudflared -CertPath $certPath

$tunnel = Ensure-Tunnel -CloudflaredPath $cloudflared -TunnelName $tunnelName
$tunnelId = $tunnel.id
if (-not $tunnelId) {
    throw "Tunnel ID was not returned for $tunnelName."
}

$credentialsPath = Join-Path $cloudflareDir "$tunnelId.json"
if (-not (Test-Path $credentialsPath)) {
    throw "Tunnel credentials file not found at $credentialsPath"
}

Write-TunnelConfig -ConfigPath $configPath -TunnelId $tunnelId -CredentialsPath $credentialsPath -Hostname $hostname
Ensure-DnsRoute -CloudflaredPath $cloudflared -TunnelName $tunnelName -Hostname $hostname
Start-NamedTunnel -CloudflaredPath $cloudflared -ConfigPath $configPath -LogPath $logPath -PidPath $pidPath
Wait-TunnelProcessReady -PidPath $pidPath -LogPath $logPath

$publicApiUrl = "https://$hostname/api/stats"
$publicDocsUrl = "https://$hostname/docs"
$publicApiBody = Wait-PublicApiReady -Url $publicApiUrl -LogPath $logPath

$publicUrlFile = Join-Path $toolsDir "public-url.txt"
Set-Content -Path $publicUrlFile -Value ("https://{0}/" -f $hostname) -Encoding ASCII

Start-Process $publicDocsUrl

Write-Host ""
Write-Host "CyberVis is available through Cloudflare Tunnel."
Write-Host "Public API:  $publicApiUrl"
Write-Host "Public docs: $publicDocsUrl"
Write-Host "Tunnel name: $tunnelName"
Write-Host "Tunnel ID:   $tunnelId"
Write-Host "Saved URL:   $publicUrlFile"
Write-Host ""
Write-Host "API /stats response:"
Write-Host $publicApiBody
