# Развёртывание на Render.com (бесплатный хостинг)

## Предварительные требования
- GitHub аккаунт (бесплатно)
- Render аккаунт (бесплатно, регистрация через GitHub)

## Шаг 1: Подготовить GitHub репозиторий

1) Если у вас ещё нет репозитория локально:
```bash
cd cyber-vis
git init
git add .
git commit -m "Initial commit"
```

2) Создать репозиторий на GitHub: https://github.com/new
   - Имя: `Diplom-cyber-security` (или как вы называли)
   - Private или Public — выбирайте

3) Подключить удалённый репозиторий и запушить:
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## Шаг 2: Регистрация на Render.com

1) Перейти на https://render.com (или login, если уже есть аккаунт)
2) Нажать **"Sign up"** → выбрать **"Continue with GitHub"**
3) Авторизовать доступ к GitHub репозиториям

## Шаг 3: Создание сервиса на Render

1) На главной Render нажать **"+ New"** → **"Web Service"**

2) **Connect a repository:**
   - Выбрать `Diplom-cyber-security` (или поиск по названию)
   - Нажать **"Connect"**

3) **Configure the service:**
   - **Name:** `cyber-vis-api` (или как хотите)
   - **Environment:** `Python 3`
   - **Build Command:** (оставить пусто, Render автоматически найдёт requirements.txt)
   - **Start Command:** 
     ```
     uvicorn server:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan:** выбрать **"Free"** ⭐ (важно!)
   - Нажать **"Create Web Service"**

## Шаг 4: Ожидание развёртывания

- Render начнёт собирать приложение (install dependencies → start server)
- Это может занять **2-5 минут** в первый раз
- Когда появится зелёная точка и надпись **"Live"** — сервер готов!

## Шаг 5: Получить публичный URL сервера

На странице сервиса в правом верхнем углу вы увидите URL вида:
```
https://cyber-vis-api.onrender.com
```

Скопировать этот URL — он используется для подключения фронтенда.

## Шаг 6: Обновить конфигурацию фронтенда

Теперь нужно указать фронтенду адрес бэкенда. Есть два способа:

### Способ A: Добавить в `index.html` и `monitor.html` (в папке вашего фронтенда)
Вставить в `<head>` (перед основным скриптом):
```html
<script>
  window.CYBER_VIS_API_BASE = 'https://cyber-vis-api.onrender.com';
  window.CYBER_VIS_WS_URL = 'wss://cyber-vis-api.onrender.com/ws/monitor';
</script>
```

### Способ B: Использовать текущий хост (автоматический)
Если GitHub Pages и API на одном хосте — ничего не менять, скрипты сами определят домен.

> **Важно:** Замените `https://cyber-vis-api.onrender.com` на ваш реальный URL с Render!

## Шаг 7: Тестирование API

Откройте в браузере:
```
https://cyber-vis-api.onrender.com/docs
```
Вы увидите интерактивную документацию Swagger-UI — это означает, что сервер работает!

Попробуйте запрос **POST /api/auth/login**:
```json
{
  "username": "test",
  "password": "test123",
  "client_type": "web"
}
```

## Что может пойти не так

### ❌ "Application failed to start"
- Проверить логи: нажать **"Logs"** на странице сервиса
- Убедиться, что `server.py` находится в корне папки `cyber-vis`
- Проверить, что все зависимости в `requirements.txt`

### ❌ "WebSocket connection failed"
- Убедиться, что используется **WSS** (не WS)
- Провериться, что URL правильный: `wss://cyber-vis-api.onrender.com/ws/monitor`

### ❌ "Build Command failed"
- Render может не найти `requirements.txt` — проверить путь
- Если файл в папке `/cyber-vis/` — создать `render.yaml` (уже сделано)

## Бесплатная версия Render: ограничения

✅ **Включено:**
- 512 MB ОЗУ
- 0.5 vCPU (shared)
- HTTPS/WSS
- Бесплатно 24/7

❌ **Ограничения:**
- После 15 минут неактивности сервис переходит в режим сна
- При первом запросе после сна — задержка ~30 сек (cold start)
- Нет гарантии 100% uptime

**Совет:** если нужно избежать sleep — можно подключить мониторинг (https://uptimerobot.com) с бесплатным пингом каждые 5 минут.

## Что дальше

После развёртывания сервера на Render:

1) ✅ API доступен по HTTPS
2) ✅ WebSocket работает по WSS
3) ✅ GitHub Pages фронтенд может подключаться к любому удалённому серверу
4) 🚀 Оба деплоя (фронтенд на GitHub Pages + бэкенд на Render) работают онлайн!

---

**Нужна помощь?** Напишите логи из Render (копировать из раздела "Logs") — помогу диагностировать проблему.
