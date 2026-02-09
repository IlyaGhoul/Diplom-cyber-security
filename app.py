"""
Wrapper для запуска FastAPI приложения из папки cyber-vis
"""
import sys
from pathlib import Path

# Добавляем папку cyber-vis в путь Python
sys.path.insert(0, str(Path(__file__).parent / "cyber-vis"))

# Импортируем FastAPI приложение
from server import app

# Теперь uvicorn может найти "app:app"
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
