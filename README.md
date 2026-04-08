# CyberVis

Diploma project for monitoring login attempts in real time.

Current recommended deployment:
- frontend on GitHub Pages
- FastAPI + SQLite on a Windows server
- HTTPS/WSS for the API through Caddy

## Architecture

- GitHub Pages serves the dashboard over `https://`
- `Caddy` terminates TLS on the Windows server
- `Caddy` proxies requests to FastAPI in Docker
- SQLite is stored in Docker volume `sqlite_data`

For the browser this means:
- frontend: `https://<github-pages-site>`
- API: `https://api.<your-domain>`
- WebSocket: `wss://api.<your-domain>/ws/monitor`

## Required Before Launch

1. A domain or subdomain for the API, for example `api.cybattack.ru`
2. DNS `A` record:
   `api.cybattack.ru -> 78.29.55.68`
3. Open inbound ports on the Windows server:
   - `80/tcp`
   - `443/tcp`
4. Docker Desktop or Docker Engine running on the server

## Environment

Main values in [`.env.example`](d:/Диплом__НА__2026__год/Программирование/Diplom-cyber-security/.env.example):

- `CYBER_VIS_DB_PATH=/data/login_attempts.db`
- `API_PORT=8000`
- `CYBER_VIS_API_BASE=https://api.example.com`
- `CYBER_VIS_DOMAIN=api.example.com`

In the current local [`.env`](d:/Диплом__НА__2026__год/Программирование/Diplom-cyber-security/.env) the project is configured for:

- `CYBER_VIS_API_BASE=https://api.cybattack.ru`
- `CYBER_VIS_DOMAIN=api.cybattack.ru`

Replace those values if you decide to use another domain.

## Launch Plan

1. Point the domain to the static IP `78.29.55.68`
2. Open Windows Firewall inbound rules for ports `80` and `443`
3. In the project root run:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml up -d --build
```

4. Check containers:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml ps
```

5. Check logs:

```powershell
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 caddy
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 api
```

6. Verify in browser:
- `https://api.cybattack.ru/docs`

If that opens, TLS and reverse proxy are working.

## GitHub Pages Frontend

The GitHub Pages site must point to the HTTPS API domain, not to the raw IP.

Use:

```powershell
python update_api_urls.py https://api.cybattack.ru "D:\Диплом__НА__2026__год\Программирование\Host\cybattack.ru.github.io"
```

Then commit and push the updated frontend files to GitHub Pages.

## Desktop Client

On Windows:

```powershell
$env:CYBER_VIS_API_BASE="https://api.cybattack.ru"
python .\cyber-vis\desktop_app.py
```

On Linux/macOS:

```bash
export CYBER_VIS_API_BASE="https://api.cybattack.ru"
python3 ./cyber-vis/desktop_app.py
```

## Notes

- A static IP by itself does not solve browser security restrictions for GitHub Pages.
- GitHub Pages needs the backend to be available over `https://`, so Caddy plus a domain is the correct setup.
- The temporary `site/` directory in this repository is no longer part of the main deployment path for the GitHub Pages setup.
