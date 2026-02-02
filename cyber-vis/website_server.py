"""
Сервер для веб-сайта мониторинга
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

# Получаем абсолютный путь к проекту
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "src" / "cyber_vis" / "app" / "templates"

app = FastAPI()

@app.get("/")
async def serve_monitor():
    """Главная страница мониторинга"""
    file_path = TEMPLATES_DIR / "monitor.html"
    
    if not file_path.exists():
        print(f"⚠️  Файл не найден: {file_path}")
        print(f"📁 Проверьте путь: {TEMPLATES_DIR}")
        return {"error": "Файл не найден", "path": str(file_path)}
    
    print(f"✅ Отдаю файл: {file_path}")
    return FileResponse(file_path)

@app.get("/index.html")
async def serve_index():
    """Страница index.html (если есть)"""
    file_path = TEMPLATES_DIR / "index.html"
    
    if file_path.exists():
        return FileResponse(file_path)
    return FileResponse(TEMPLATES_DIR / "monitor.html")

if __name__ == "__main__":
    print("=" * 50)
    print("🌐 Веб-сайт мониторинга Cyber-Vis")
    print(f"📁 Папка templates: {TEMPLATES_DIR}")
    print(f"✅ Monitor.html существует: {(TEMPLATES_DIR / 'monitor.html').exists()}")
    print(f"🌍 Сайт доступен: http://localhost:8080")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8080)