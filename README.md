# CyberVis

Diploma project for monitoring login attempts in real time.

## Recommended Deployment

- Frontend on GitHub Pages
- FastAPI + SQLite on a Windows server
- Caddy on the same server for HTTPS and WSS termination

For direct launch in a local network or behind a router without a domain, this repository also includes an HTTP-only profile with automatic LAN IP detection.

## Architecture

- GitHub Pages serves the dashboard over `https://`
- The backend must therefore be available over `https://` as well
- `Caddy` terminates TLS for `api.<your-domain>` and proxies to FastAPI in Docker
- SQLite is stored in Docker volume `sqlite_data`

Browser-facing endpoints:

- frontend: `https://<github-pages-site>`
- API: `https://api.<your-domain>/`
- WebSocket: `wss://api.<your-domain>/ws/monitor`

A static or public IP alone is not enough for GitHub Pages. The browser needs the API on an HTTPS domain such as `https://api.cybattack.ru/`, not on a raw `http://` IP address.

## Direct Local Network Launch

If your machine has a local address such as `192.168.x.x` and the public IP may change, use the included launcher. It detects the current LAN IP automatically and starts the HTTP stack:

```powershell
C:\Users\user\Desktop\CyberVis Start Server.cmd
```

It will:

- start Docker Desktop if needed
- detect the current LAN IP
- update `.env` with `CYBER_VIS_API_BASE=http://<current-lan-ip>/`
- start `docker compose -f compose.yaml -f compose.ip.yaml up -d --build`
- open `http://localhost/docs`

After launch, the service is available:

- locally on `http://localhost/docs`
- from other devices in the same network on `http://<current-lan-ip>/docs`
- from the internet only if your router forwards port `80` to this machine

Desktop launcher:

- `C:\Users\user\Desktop\CyberVis Start Server.cmd`

## What You Need Before Launch

1. A domain or subdomain for the API, for example `api.cybattack.ru`
2. DNS `A` record:
   `api.cybattack.ru -> 78.29.55.68`
3. Open inbound ports on the Windows server:
   - `80/tcp`
   - `443/tcp`
4. Docker Desktop or Docker Engine running on the server

## Environment

Create `.env` in the project root by copying `.env.example`:

```powershell
Copy-Item .env.example .env
```

For the `api.cybattack.ru` deployment, set:

```dotenv
CYBER_VIS_DB_PATH=/data/login_attempts.db
API_PORT=8000
CYBER_VIS_DOMAIN=api.cybattack.ru
CYBER_VIS_API_BASE=https://api.cybattack.ru/
```

If you use another domain, replace both `CYBER_VIS_DOMAIN` and `CYBER_VIS_API_BASE`.

## Windows Server Launch Checklist

1. Create the DNS record:
   `api.cybattack.ru -> 78.29.55.68`
2. Open Windows Firewall inbound rules for `80/tcp` and `443/tcp`:

```powershell
New-NetFirewallRule -DisplayName "CyberVis HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "CyberVis HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

3. Start the stack from the project root:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml up -d --build
```

4. Check container status:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml ps
```

5. Check logs:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 caddy
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 api
```

6. Verify in the browser:
   `https://api.cybattack.ru/docs`

If that page opens, HTTPS and reverse proxying are working.

## GitHub Pages Frontend

The GitHub Pages site must point to the HTTPS API domain, not to the raw IP.

Update the frontend files:

```powershell
python update_api_urls.py https://api.cybattack.ru/ "D:\path\to\cybattack.ru.github.io"
```

Then commit and push the updated frontend repository.

## Desktop Client

On Windows:

```powershell
$env:CYBER_VIS_API_BASE="https://api.cybattack.ru/"
python .\cyber-vis\desktop_app.py
```

On Linux or macOS:

```bash
export CYBER_VIS_API_BASE="https://api.cybattack.ru/"
python3 ./cyber-vis/desktop_app.py
```

## Notes

- `compose.caddy.yaml` and `Caddyfile` already implement the TLS proxy path for this deployment model.
- For home or office networks, the server usually runs on a LAN IP like `192.168.x.x`; the router handles internet access.
- The temporary `site/` directory is not part of the GitHub Pages deployment flow.
- External browser clients should use the HTTPS domain, not `http://<server-ip>:8000`.
