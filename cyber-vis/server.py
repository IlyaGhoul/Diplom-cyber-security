"""
FastAPI сервер с WebSocket для системы мониторинга
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response  # Добавили Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import json
from datetime import datetime
import os
import sys
import time
import logging
import uvicorn
import asyncio
import sqlite3
import requests
import ipaddress

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from database import db

app = FastAPI(title="Login Monitor API", version="1.0")

logger = logging.getLogger("cyber_vis")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def extract_client_ip(headers: dict, fallback: str) -> str:
    return (
        headers.get("cf-connecting-ip")
        or headers.get("x-forwarded-for", "").split(",")[0].strip()
        or headers.get("x-real-ip")
        or fallback
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    headers = {k.lower(): v for k, v in request.headers.items()}
    client_ip = extract_client_ip(headers, request.client.host if request.client else "unknown")
    cf_ray = headers.get("cf-ray", "-")
    cf_country = headers.get("cf-ipcountry", "-")
    logger.info(
        "HTTP %s %s %s %.1fms client=%s cf_ray=%s cf_country=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        client_ip,
        cf_ray,
        cf_country,
    )
    return response

@app.on_event("startup")
async def configure_event_loop():
    if os.name != "nt":
        return
    loop = asyncio.get_running_loop()
    def exception_handler(loop, context):
        exception = context.get("exception")
        winerror = getattr(exception, "winerror", None)
        if isinstance(exception, OSError) and winerror in {64, 10054, 995}:
            return
        loop.default_exception_handler(context)
    loop.set_exception_handler(exception_handler)

# Разрешаем CORS для всех доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# Модель запроса
class LoginRequest(BaseModel):
    username: str
    password: str
    client_type: str = "desktop"
    user_agent: Optional[str] = "unknown"
    ip_address: Optional[str] = None  # optional client-supplied IP (preferred if present)

# Модель ответа
class LoginResponse(BaseModel):
    success: bool
    message: str

# Функция для получения IP-адреса
def get_client_ip(request: Request) -> str:
    """Получение реального IP-адреса клиента"""
    # Пробуем получить из заголовка X-Forwarded-For (если за прокси)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Берем первый IP из списка
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    
    # Пробуем получить из заголовка X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Если заголовков нет, используем host
    if request.client and request.client.host:
        return request.client.host
    
    return "127.0.0.1"  # fallback

# Функция для получения страны по IP
def get_country_by_ip(ip_address: str) -> str:
    """Получить страну по IP-адресу"""
    if not ip_address or ip_address == "127.0.0.1" or ip_address == "::1":
        return "Локальное"
    
    try:
        # Используем ipwhois.app API (бесплатно, без ключа)
        response = requests.get(f'https://ipwhois.app/json/{ip_address}', timeout=2)
        if response.ok:
            data = response.json()
            country = data.get('country')
            if country:
                return country
    except Exception as e:
        print(f"⚠️  Ошибка определения страны для IP {ip_address}: {e}")
    
    return "Неизвестно"

def _to_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def is_local_ip(ip_address: str) -> bool:
    try:
        parsed_ip = ipaddress.ip_address(ip_address)
        return parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local
    except ValueError:
        return not ip_address or ip_address.lower() == "localhost"

def get_geo_by_ip(ip_address: str) -> dict:
    """Get country/city/coordinates for the attack map."""
    fallback = {
        "country": "Локальное" if is_local_ip(ip_address or "") else "Неизвестно",
        "city": None,
        "latitude": None,
        "longitude": None,
    }

    if not ip_address or is_local_ip(ip_address):
        return fallback

    try:
        response = requests.get(f"https://ipwhois.app/json/{ip_address}", timeout=2)
        if response.ok:
            data = response.json()
            if data.get("success") is False:
                return fallback
            return {
                "country": data.get("country") or fallback["country"],
                "city": data.get("city"),
                "latitude": _to_float(data.get("latitude")),
                "longitude": _to_float(data.get("longitude")),
            }
    except Exception as e:
        print(f"⚠️ Ошибка определения геолокации для IP {ip_address}: {e}")

    return fallback

def classify_attempt(success: bool, failed_attempts_before: int) -> tuple[str, str]:
    if success:
        return "successful_login", "low"
    if failed_attempts_before >= 2:
        return "brute_force", "high"
    return "failed_login", "medium"

# Хеш паролей
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Создаем словарь с хешированными паролями
RAW_USERS = {
    "ilya": "1111",
    "admin": "admin123",
    "test": "test123",
    "user": "password"
}

USERS = {username: hash_password(password) for username, password in RAW_USERS.items()}

# WebSocket подключения для мониторинга
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        headers = {k.lower(): v for k, v in websocket.headers.items()}
        client_ip = extract_client_ip(headers, websocket.client.host if websocket.client else "unknown")
        cf_ray = headers.get("cf-ray", "-")
        cf_country = headers.get("cf-ipcountry", "-")
        logger.info(
            "WS CONNECT client=%s cf_ray=%s cf_country=%s total=%s",
            client_ip,
            cf_ray,
            cf_country,
            len(self.active_connections),
        )
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WS DISCONNECT total=%s", len(self.active_connections))
            
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)
            
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """Обработка попытки входа"""
    # Предпочитаем IP, присланный клиентом (если есть), иначе определяем серверно
    client_ip = request.ip_address or get_client_ip(http_request)
    
    # НОВОЕ: Проверяем, заблокирован ли IP
    is_blocked, block_reason = db.is_ip_blocked(client_ip)
    if is_blocked:
        print(f"🚫 Попытка входа с заблокированного IP: {client_ip} - {block_reason}")
        return LoginResponse(
            success=False,
            message=block_reason
        )
    
    print(f"🔍 Попытка входа:")
    print(f"   Пользователь: {request.username}")
    print(f"   IP-адрес: {client_ip}")
    print(f"   Введенный пароль: {request.password}")
    print(f"   Хеш введенного пароля: {hash_password(request.password)}")
    print(f"   Сохраненный хеш: {USERS.get(request.username)}")
    
    # Получаем сохраненный хеш пароля для пользователя
    saved_password_hash = USERS.get(request.username)
    
    # Хешируем введенный пароль
    input_password_hash = hash_password(request.password)
    
    # Проверяем учетные данные - сравниваем хеши
    is_valid = False
    reason = ""
    
    if request.username in USERS and input_password_hash == saved_password_hash:
        is_valid = True
        reason = "Успешная авторизация"
        message = f"Добро пожаловать, {request.username}!"
        print(f"   ✅ Авторизация успешна")
    else:
        is_valid = False
        if request.username in USERS:
            reason = "Неверный пароль"
            print(f"   ❌ Неверный пароль")
            print(f"   Введенный хеш: {input_password_hash}")
            print(f"   Ожидаемый хеш: {saved_password_hash}")
        else:
            reason = "Пользователь не найден"
            print(f"   ❌ Пользователь не найден")
        message = "Неверный логин или пароль"
    
    failed_attempts_before = 0 if is_valid else db.get_failed_attempts_count(client_ip, minutes=15)
    attack_type, threat_level = classify_attempt(is_valid, failed_attempts_before)
    geo = await asyncio.to_thread(get_geo_by_ip, client_ip)

    # Сохраняем попытку в БД ПЕРЕД проверкой блокировки
    attempt_id = db.add_attempt(
        username=request.username,
        ip_address=client_ip,  # Используем реальный IP
        client_type=request.client_type,
        success=is_valid,
        reason=reason,
        user_agent=request.user_agent,
        country=geo["country"],
        city=geo["city"],
        latitude=geo["latitude"],
        longitude=geo["longitude"],
        attack_type=attack_type,
        threat_level=threat_level,
        metadata={
            "timestamp": datetime.now().isoformat(),
            "client_info": {
                "type": request.client_type,
                "user_agent": request.user_agent,
                "ip_address": client_ip
            },
            "geo": geo,
            "attack_type": attack_type,
            "threat_level": threat_level
        }
    )
    
    print(f"   Попытка сохранена с ID: {attempt_id}")
    
    # НОВОЕ: Если ошибка - считаем попытки (теперь включая текущую) и автоматически блокируем
    if not is_valid:
        failed_count_15min = db.get_failed_attempts_count(client_ip, minutes=15)
        failed_count_60min = db.get_failed_attempts_count(client_ip, minutes=60)
        
        print(f"   ⚠️  Неудачных попыток за 15 мин: {failed_count_15min}, за 60 мин: {failed_count_60min}")
        print(f"   📊 Проверка блокировки: success={is_valid}, reason={reason}")
        
        # Правило 1: 3 ошибки за 15 минут = 10 минут блокировки
        if failed_count_15min >= 3:
            db.add_ip_block(client_ip, reason="Слишком много неудачных попыток (3+ за 15 мин)", 
                          duration_minutes=10, is_permanent=False)
            print(f"   🚫 IP {client_ip} заблокирован на 10 минут (правило 1)")
            # Отправляем событие о блокировке
            await manager.broadcast({
                "type": "ip_blocked",
                "data": {"ip_address": client_ip, "reason": "3+ ошибки за 15 минут"},
                "timestamp": datetime.now().isoformat()
            })
            return LoginResponse(
                success=False,
                message="⏱️ IP заблокирован на 10 минут из-за частых ошибок. Попробуйте позже."
            )
        
        # Правило 2: 10 ошибок за 60 минут = 24 часа блокировки
        if failed_count_60min >= 10:
            db.add_ip_block(client_ip, reason="Слишком много неудачных попыток (10+ за час)", 
                          duration_minutes=24*60, is_permanent=False)
            print(f"   🚫 IP {client_ip} заблокирован на 24 часа (правило 2)")
            # Отправляем событие о блокировке
            await manager.broadcast({
                "type": "ip_blocked",
                "data": {"ip_address": client_ip, "reason": "10+ ошибок за час"},
                "timestamp": datetime.now().isoformat()
            })
            return LoginResponse(
                success=False,
                message="⏱️ IP заблокирован на 24 часа из-за многочисленных ошибок."
            )
    
    # Получаем полные данные о попытке
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM login_attempts WHERE id = ?', (attempt_id,))
        row = cursor.fetchone()
        
        attempt_data = {}
        if row:
            columns = [desc[0] for desc in cursor.description]
            attempt_data = dict(zip(columns, row))
            attempt_data['success'] = bool(attempt_data['success'])
    
    # Отправляем событие мониторам
    await manager.broadcast({
        "type": "login_attempt",
        "data": attempt_data,
        "timestamp": datetime.now().isoformat()
    })
    
    return LoginResponse(
        success=is_valid,
        message=message
    )

@app.get("/api/stats")
async def get_stats():
    """Получить статистику"""
    return {
        "success": True,
        "data": db.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/attempts")
async def get_attempts(limit: int = 100):
    """Получить историю попыток"""
    attempts = db.get_recent_attempts(limit)
    
    return {
        "success": True,
        "data": attempts,
        "count": len(attempts),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/attack-map")
async def get_attack_map(limit: int = 200):
    """Получить попытки с координатами для карты атак"""
    attempts = db.get_geo_attempts(limit)

    return {
        "success": True,
        "data": attempts,
        "count": len(attempts),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/blocked-ips")
async def get_blocked_ips():
    """Получить список заблокированных IP адресов"""
    blocked_ips = db.get_blocked_ips()
    
    return {
        "success": True,
        "data": blocked_ips,
        "count": len(blocked_ips),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/chart_data")
async def get_chart_data():
    """Получить данные для графика - только успешные и неудачные попытки"""
    # ИСПРАВЛЕНО: используем новое соединение вместо db.conn
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        
        try:
            # Получаем общее количество успешных и неудачных попыток
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                    COUNT(CASE WHEN success = 0 THEN 1 END) as failed
                FROM login_attempts
            ''')
            
            row = cursor.fetchone()
            successful = row[0] or 0
            failed = row[1] or 0
            
            chart_data = {
                "total": {
                    "successful": successful,
                    "failed": failed,
                    "total": successful + failed
                }
            }
            
            return {
                "success": True,
                "data": chart_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения данных графика: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket для мониторинга в реальном времени"""
    await manager.connect(websocket)
    
    try:
        # Отправляем начальные данные
        await manager.send_personal_message({
            "type": "init",
            "data": {
                "stats": db.get_stats(),
                "recent_attempts": db.get_recent_attempts(20),
                "chart_data": {
                    "total": {
                        "successful": db.get_stats()["successful"],
                        "failed": db.get_stats()["failed"],
                        "total": db.get_stats()["total_attempts"]
                    }
                }
            },
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # Бесконечный цикл для поддержания соединения
        while True:
            try:
                # Ожидаем сообщение от клиента с таймаутом
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                # Обрабатываем пинг
                if data.strip().lower() == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                elif data.strip().lower() == "get_stats":
                    # По запросу отправляем обновленную статистику
                    await manager.send_personal_message({
                        "type": "stats_update",
                        "data": db.get_stats(),
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                    
            except asyncio.TimeoutError:
                # Таймаут - отправляем keep-alive сообщение
                try:
                    await manager.send_personal_message({
                        "type": "keep_alive",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                except:
                    break  # Соединение разорвано
                    
    except WebSocketDisconnect:
        logger.info("WS DISCONNECT client закрыт соединение")
    except Exception as e:
        logger.error("WS ERROR: %s", e)
    finally:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    """Информация о сервере"""
    return {
        "service": "Login Monitor API",
        "version": "1.0",
        "endpoints": {
            "login": "POST /api/auth/login",
            "stats": "GET /api/stats",
            "attempts": "GET /api/attempts",
            "attack_map": "GET /api/attack-map",
            "chart_data": "GET /api/chart_data",
            "websocket": "WS /ws/monitor"
        },
        "demo_users": list(RAW_USERS.keys())
    }

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Сервер мониторинга запущен")
    print("📡 API: http://localhost:8000")
    print("📊 Веб-мониторинг: http://localhost:8080")
    print("👤 Демо пользователи:", list(RAW_USERS.keys()))
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=30
    )
