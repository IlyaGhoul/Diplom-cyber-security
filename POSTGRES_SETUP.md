# Миграция на PostgreSQL (Render)

## 📋 Что изменилось

Проект был мигрирован с **SQLite** на **PostgreSQL** для сохранения данных между перезагрузками контейнера на Render.

### Преимущества PostgreSQL

- ✅ Данные сохраняются **навсегда** (persistent storage)
- ✅ Доступен **бесплатный план** на Render
- ✅ Автоматические **резервные копии**
- ✅ Лучшая **производительность** с индексами

## 🚀 Развёртывание на Render

### Шаг 1: Создайте PostgreSQL базу на Render

1. Перейдите на [render.com](https://render.com)
2. Войдите в аккаунт
3. Создайте новый **PostgreSQL Database** (выберите бесплатный план)
4. Вы получите строку подключения вида:
   ```
   postgresql://username:password@hostname:5432/database_name
   ```

### Шаг 2: Добавьте переменную окружения на Render

В настройках FastAPI сервиса на Render:

1. Перейдите в **Environment**
2. Добавьте переменную:
   ```
   DATABASE_URL = postgresql://username:password@hostname:5432/database_name
   ```
3. Сохраните и перезагрузите сервис

### Шаг 3: Убедитесь, что `psycopg2-binary` в requirements.txt

```txt
psycopg2-binary>=2.9.0
```

## 📝 Локальная разработка

### Вариант 1: Используйте локальный PostgreSQL

```bash
# Установите PostgreSQL (Windows/macOS/Linux)
# Затем установите зависимости
pip install -r requirements.txt

# Экспортируйте DATABASE_URL (Linux/macOS):
export DATABASE_URL="postgresql://user:password@localhost:5432/login_monitor"

# или на Windows (PowerShell):
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/login_monitor"

# Запустите сервер
python -m uvicorn cyber_vis.server:app --reload
```

### Вариант 2: SQLite для локальной разработки (бэкап)

Если вам нужен SQL ite локально, скопируйте старую версию `database.py` и переключайтесь контекстно.

## 📊 Структура БД на PostgreSQL

### Таблица `login_attempts`

| Поле | Тип | Описание |
|------|-----|---------|
| id | SERIAL | Первичный ключ |
| username | TEXT | Имя пользователя |
| ip_address | TEXT | IP адрес клиента |
| country | TEXT | Страна геолокации |
| client_type | TEXT | Тип клиента (desktop/web) |
| success | BOOLEAN | Успешность входа |
| reason | TEXT | Причина ошибки |
| attempt_time | TIMESTAMP | Время попытки |
| user_agent | TEXT | User-Agent браузера |
| metadata | JSONB | Доп. данные (JSON) |

### Таблица `ip_blocks`

| Поле | Тип | Описание |
|------|-----|---------|
| id | SERIAL | Первичный ключ |
| ip_address | TEXT | IP адрес (уникальный) |
| reason | TEXT | Причина блокировки |
| blocked_until | TIMESTAMP | Время разблокировки |
| is_permanent | BOOLEAN | Постоянная ли блокировка |
| created_at | TIMESTAMP | Когда заблокирован |

## 🔍 Проверка подключения

### Тестовый скрипт

```python
import os
import psycopg2

database_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/login_monitor')

try:
    conn = psycopg2.connect(database_url)
    print("✅ PostgreSQL подключён успешно!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"PostgreSQL версия: {cursor.fetchone()}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
```

## 🆘 Частые ошибки

### `psycopg2.OperationalError: could not connect to server`

- Проверьте `DATABASE_URL` в переменных окружения
- Убедитесь, что PostgreSQL сервис запущен
- Проверьте правильность хоста и порта

### `psycopg2: module not found`

```bash
pip install psycopg2-binary
```

### Данные теряются при деплое

Это нормально **только если вы используете SQLite**. PostgreSQL данные сохраняет автоматически.

## 📚 Документация

- [psycopg2 документация](https://www.psycopg.org/psycopg2/docs/)
- [Render PostgreSQL Guide](https://render.com/docs/databases)
- [PostgreSQL Cheatsheet](https://www.postgresql.org/docs/)
