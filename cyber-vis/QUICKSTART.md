# Быстрый старт — локальное тестирование

Перед развёртыванием на Render рекомендуется протестировать локально.

## 1️⃣ Установка зависимостей

```bash
cd cyber-vis
pip install -r requirements.txt
```

## 2️⃣ Запуск сервера локально

```bash
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Вы должны увидеть:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## 3️⃣ Проверка API

Откройте браузер и перейдите на:
```
http://localhost:8000/docs
```

Вы увидите интерактивную Swagger-UI документацию.

Попробуйте **POST /api/auth/login**:
```json
{
  "username": "admin",
  "password": "admin123",
  "client_type": "web"
}
```

✅ Если получили `{"success": true, "message": "..."}` — сервер работает!

## 4️⃣ Запуск веб-мониторинга (опционально)

В отдельном терминале:
```bash
python website_server.py
```

Откройте: http://localhost:8080

## 5️⃣ Готово, можно деплоить!

После тестирования локально → следуйте [DEPLOYMENT_RU.md](DEPLOYMENT_RU.md)

---

## Возможные проблемы

### ❌ "ModuleNotFoundError: No module named 'fastapi'"
Решение: установить зависимости `pip install -r requirements.txt`

### ❌ "Address already in use" (порт 8000 занят)
Решение: либо закрыть другое приложение на порту 8000, либо запустить на другом переводе:
```bash
uvicorn server:app --port 8001
```

### ❌ "Cannot import database"
Убедиться, что запуск из папки `cyber-vis/` и файл `database.py` в той же папке.

## Быстрые команды для Windows PowerShell

```powershell
# Перейти в папку проекта
cd cyber-vis

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000

# Или запустить веб-мониторинг
python website_server.py
```
