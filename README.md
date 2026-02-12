# CyberVis

Diploma project for monitoring and visualizing login attempts in real time.

## How It Works
1. Desktop client sends login attempts to the API endpoint `/api/auth/login`.
2. API stores attempts in PostgreSQL.
3. API pushes new attempts to the WebSocket `/ws/monitor`.
4. The website updates the dashboard in real time.

## Project Structure
- Backend (API + DB): this repository.
- Frontend (website): `D:\Диплом__НА__2026__год\Программирование\Host`.
- Desktop client: `cyber-vis/desktop_app.py`.

## Run On VPS With HTTPS/WSS (Recommended)
Prerequisites:
- DNS `A` record for `api.<your-domain>` pointing to the VPS IP.
- Ports `80` and `443` open on the VPS.
- Docker installed.

Steps:
```bash
cd /root/Diplom-cyber-security
cp .env.example .env
```
Edit `.env` and set:
```
POSTGRES_PASSWORD=strong_password
CYBER_VIS_DOMAIN=api.cybattack.ru
```
Start services:
```bash
docker compose -f compose.yaml -f compose.caddy.yaml up -d --build
```
Check:
```
https://api.cybattack.ru/docs
```

## Local Test (No HTTPS)
```powershell
docker compose up -d --build
```
API docs:
```
http://localhost:8000/docs
```

## Configure The Frontend
The website is stored in:
```
D:\Диплом__НА__2026__год\Программирование\Host
```
Update API and WebSocket URLs:
```powershell
python update_api_urls.py https://api.cybattack.ru "D:\Диплом__НА__2026__год\Программирование\Host\cybattack.ru.github.io"
```
For local testing:
```powershell
python update_api_urls.py http://localhost:8000 "D:\Диплом__НА__2026__год\Программирование\Host\cybattack.ru.github.io"
cd "D:\Диплом__НА__2026__год\Программирование\Host\cybattack.ru.github.io"
python -m http.server 5173
```
Open:
```
http://localhost:5173/index.html
```

If you use GitHub Pages, commit and push the updated HTML files.

## Run Desktop Client
On your PC:
```powershell
$env:CYBER_VIS_API_BASE="https://api.cybattack.ru"
python .\cyber-vis\desktop_app.py
```
Linux/macOS:
```bash
export CYBER_VIS_API_BASE="https://api.cybattack.ru"
python3 ./cyber-vis/desktop_app.py
```

## Useful Commands
```bash
docker compose -f compose.yaml -f compose.caddy.yaml ps
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 caddy
docker compose -f compose.yaml -f compose.caddy.yaml logs --tail=100 api
```
