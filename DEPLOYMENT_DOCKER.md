# Docker Compose Deployment

This project supports two Docker-based deployment modes:

- local development over `http://localhost:8000`
- direct HTTP launch on the current LAN IP with an auto-detecting launcher
- production deployment for GitHub Pages via `https://api.<your-domain>/` and Caddy

## 1. Preparation

Install Docker and Docker Compose, then create `.env` in the project root:

```powershell
Copy-Item .env.example .env
```

Base variables:

```dotenv
CYBER_VIS_DB_PATH=/data/login_attempts.db
API_PORT=8000
```

For GitHub Pages production, also set:

```dotenv
CYBER_VIS_DOMAIN=api.cybattack.ru
CYBER_VIS_API_BASE=https://api.cybattack.ru/
```

## 2. Local Docker Run

Start only the API stack:

```powershell
docker compose up -d --build
```

Check status:

```powershell
docker compose ps
docker compose logs -f api
```

Open API docs:

- `http://localhost:8000/docs`
- or `http://localhost:<API_PORT>/docs`

## 3. Production for GitHub Pages

If the frontend is hosted on GitHub Pages, the browser will block `http://...` and `ws://...` calls from an HTTPS page. The backend must be published on an HTTPS domain.

Required production setup:

1. Create a DNS `A` record:
   `api.cybattack.ru -> 78.29.55.68`
2. Open inbound `80/tcp` and `443/tcp` on the Windows server
3. Keep `CYBER_VIS_DOMAIN` and `CYBER_VIS_API_BASE` pointed at the HTTPS API domain
4. Start the combined stack:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml up -d --build
```

Useful checks:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml ps
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 caddy
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 api
```

Verify:

- `https://api.cybattack.ru/docs`

If that page opens, HTTPS and reverse proxying are working.

## 3a. Direct Launch in a Local Network

If this Windows machine lives behind a router and has a local address like `192.168.x.x`, use the desktop launcher:

```powershell
C:\Users\user\Desktop\CyberVis Start Server.cmd
```

The launcher will:

- detect the current LAN IP
- update `.env` with `CYBER_VIS_API_BASE=http://<current-lan-ip>/`
- start `docker compose -f compose.yaml -f compose.ip.yaml up -d --build`
- open `http://localhost/docs`

The repository also includes a Windows launcher script:

- `launch_on_ip_78.29.55.68.ps1`
- Desktop launcher: `C:\Users\user\Desktop\CyberVis Start Server.cmd`

Access options after launch:

- local machine: `http://localhost/docs`
- another device in the same network: `http://<current-lan-ip>/docs`
- internet access only after router port forwarding to this machine

## 4. Update GitHub Pages Frontend

Point the frontend to the HTTPS API domain:

```powershell
python update_api_urls.py https://api.cybattack.ru/ "D:\path\to\cybattack.ru.github.io"
```

Then commit and push the frontend repository.

## 5. Desktop Client

Windows:

```powershell
$env:CYBER_VIS_API_BASE="https://api.cybattack.ru/"
python .\cyber-vis\desktop_app.py
```

Linux or macOS:

```bash
export CYBER_VIS_API_BASE="https://api.cybattack.ru/"
python3 ./cyber-vis/desktop_app.py
```

## 6. Why the Domain Matters

GitHub Pages is always served over HTTPS. Because of that, the browser expects:

- API over `https://api.<your-domain>/`
- WebSocket over `wss://api.<your-domain>/ws/monitor`

A static IP by itself does not solve that browser security requirement.
