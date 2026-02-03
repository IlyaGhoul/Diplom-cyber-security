"""
FastAPI сервер с WebSocket для системы мониторинга
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request  # Добавили Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import json
from datetime import datetime
import uvicorn
import asyncio
import sqlite3

from database import db

app = FastAPI(title="Login Monitor API", version="1.0")

# Разрешаем CORS для всех доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель запроса
class LoginRequest(BaseModel):
    username: str
    password: str
    client_type: str = "desktop"
    user_agent: Optional[str] = "unknown"

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
        print(f"✅ WebSocket подключен. Всего подключений: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"📴 WebSocket отключен. Осталось: {len(self.active_connections)}")
            
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
    # Получаем реальный IP-адрес
    client_ip = get_client_ip(http_request)
    
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
    
    # Сохраняем попытку в БД
    attempt_id = db.add_attempt(
        username=request.username,
        ip_address=client_ip,  # Используем реальный IP
        client_type=request.client_type,
        success=is_valid,
        reason=reason,
        user_agent=request.user_agent,
        metadata={
            "timestamp": datetime.now().isoformat(),
            "client_info": {
                "type": request.client_type,
                "user_agent": request.user_agent,
                "ip_address": client_ip
            }
        }
    )
    
    print(f"   Попытка сохранена с ID: {attempt_id}")
    
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
        print("📴 WebSocket отключен клиентом")
    except Exception as e:
        print(f"❌ WebSocket ошибка: {e}")
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