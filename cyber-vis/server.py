"""
FastAPI сервер с WebSocket для системы мониторинга
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import json
from datetime import datetime
import uvicorn
import asyncio

from database import db

app = FastAPI(title="Login Monitor API", version="1.0")

# Разрешаем CORS для всех доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все домены
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

# Предустановленные пользователи
USERS = {
    "ilya": "1111",
    "admin": "admin123",
    "test": "test123",
    "user": "password"
}

# Хеш паролей
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# WebSocket подключения для мониторинга
monitor_connections: List[WebSocket] = []

async def broadcast_to_monitors(event_type: str, data: dict):
    """Отправить событие всем мониторам"""
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Удаляем отключенные соединения
    dead_connections = []
    for websocket in monitor_connections:
        try:
            await websocket.send_json(message)
        except:
            dead_connections.append(websocket)
    
    for websocket in dead_connections:
        if websocket in monitor_connections:
            monitor_connections.remove(websocket)

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Обработка попытки входа"""
    # В реальном приложении получаем IP из запроса
    client_ip = "127.0.0.1"
    
    # Хешируем пароль для проверки
    password_hash = hash_password(request.password)
    
    # Проверяем учетные данные
    is_valid = False
    reason = ""
    
    if request.username in USERS and hash_password(USERS[request.username]) == password_hash:
        is_valid = True
        reason = "Успешная авторизация"
        message = f"Добро пожаловать, {request.username}!"
    else:
        is_valid = False
        if request.username in USERS:
            reason = "Неверный пароль"
        else:
            reason = "Пользователь не найден"
        message = "Неверный логин или пароль"
    
    # Сохраняем попытку в БД
    db.add_attempt(
        username=request.username,
        ip_address=client_ip,
        client_type=request.client_type,
        success=is_valid,
        reason=reason,
        user_agent=request.user_agent,
        metadata={
            "timestamp": datetime.now().isoformat(),
            "client_info": {
                "type": request.client_type,
                "user_agent": request.user_agent
            }
        }
    )
    
    # Отправляем событие мониторам
    await broadcast_to_monitors("login_attempt", {
        "username": request.username,
        "ip_address": client_ip,
        "client_type": request.client_type,
        "success": is_valid,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "user_agent": request.user_agent
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

@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket для мониторинга в реальном времени"""
    await websocket.accept()
    monitor_connections.append(websocket)
    
    try:
        # Отправляем начальные данные
        await websocket.send_json({
            "type": "init",
            "data": {
                "stats": db.get_stats(),
                "recent_attempts": db.get_recent_attempts(20)
            },
            "timestamp": datetime.now().isoformat()
        })
        
        # Периодически отправляем обновления
        while True:
            await asyncio.sleep(2)  # Каждые 2 секунды
            await websocket.send_json({
                "type": "stats_update",
                "data": db.get_stats(),
                "timestamp": datetime.now().isoformat()
            })
                
    except (WebSocketDisconnect, Exception) as e:
        print(f"WebSocket отключен: {e}")
    finally:
        if websocket in monitor_connections:
            monitor_connections.remove(websocket)

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
            "websocket": "WS /ws/monitor"
        },
        "demo_users": list(USERS.keys())
    }

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Сервер мониторинга запущен")
    print("📡 API: http://localhost:8000")
    print("📊 Веб-мониторинг: http://localhost:8080")
    print("👤 Демо пользователи:", list(USERS.keys()))
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)