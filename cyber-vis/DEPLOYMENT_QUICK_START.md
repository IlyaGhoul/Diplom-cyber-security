# Развёртывание Cyber-Vis на Render.com (бесплатный хостинг) 🚀

## 📋 Краткое резюме изменений

Я подготовил проект к развёртыванию на бесплатном хостинге Render.com с поддержкой HTTPS/WSS.

## ✅ Что было сделано

### 1. Клиент теперь конфигурируемый
- Фронтенд находится отдельно; укажите путь к папке сайта при запуске `update_api_urls.py`.

### 2. Добавлены файлы конфигурации для хостинга
- **`requirements.txt`** — список всех зависимостей Python
- **`Procfile`** — инструкция для Render по запуску приложения
- **`render.yaml`** — конфигурация сервиса на Render (опционально)
- **`.gitignore`** — какие файлы не загружать на GitHub

### 3. Документация
- **`DEPLOYMENT_RU.md`** — пошаговая инструкция развёртывания на Render.com ⭐
- **`QUICKSTART.md`** — как протестировать локально перед деплоем
- **`update_api_urls.py`** — скрипт для автоматического обновления URL в HTML

## 🚀 Быстрый старт (5 минут)

### Шаг 1: Подготовить GitHub репозиторий
```bash
cd cyber-vis
git init
git add .
git commit -m "Ready for deployment"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Шаг 2: Развернуть на Render
1. Перейти на https://render.com → Sign up (через GitHub)
2. New → Web Service
3. Выбрать репозиторий `cyber-vis`
4. **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. **Plan:** Free ⭐
6. Create Web Service

### Шаг 3: Подождать и получить URL
- Render будет собирать приложение (~2-5 минут)
- После появления зелёной точки скопировать URL: `https://cyber-vis-api.onrender.com`

### Шаг 4: Подключить фронтенд
Добавить в `<head>` файлов index.html и monitor.html (в папке вашего фронтенда):
```html
<script>
  window.CYBER_VIS_API_BASE = 'https://cyber-vis-api.onrender.com';
  window.CYBER_VIS_WS_URL = 'wss://cyber-vis-api.onrender.com/ws/monitor';
</script>
```

Или использовать скрипт автоматически:
```bash
python update_api_urls.py https://your-server.com "D:\path\to\site"
```

### Шаг 5: Проверить
- Откройте `https://cyber-vis-api.onrender.com/docs` — должна загрузиться документация
- Попробуйте POST запрос к `/api/auth/login`

## 📚 Полная документация

**Для подробностей:** читайте [DEPLOYMENT_RU.md](DEPLOYMENT_RU.md)

**Локальное тестирование:** читайте [QUICKSTART.md](QUICKSTART.md)

## 🆓 Что включено в FREE план Render

✅ 512 MB ОЗУ  
✅ 0.5 vCPU (shared)  
✅ HTTPS/WSS (TLS автоматический)  
✅ WebSocket поддержка  
✅ 24/7 работа  

⚠️ **Но:** сервис переходит в sleep после 15 мин неактивности (холодный старт ~30 сек)

## 🔗 Адреса после развёртывания

- **API документация:** https://cyber-vis-api.onrender.com/docs
- **API база:** https://cyber-vis-api.onrender.com
- **WebSocket:** wss://cyber-vis-api.onrender.com/ws/monitor
- **GitHub Pages фронтенд:** https://ваш-username.github.io/cybattack.ru.github.io/

## 💡 Рекомендации

1. **Перед деплоем** — тестируйте локально ([QUICKSTART.md](QUICKSTART.md))
2. **После деплоя** — добавьте мониторинг (https://uptimerobot.com) чтобы избежать sleep
3. **Хотите больше ресурсов?** — upgrade на платный план ($7/месяц)

## ❓ Нужна помощь?

**Что-то не работает?** Напишите:
- Логи из Render (раздел "Logs")
- Ваш реальный URL (вместо cyber-vis-api.onrender.com)
- Какая именно ошибка

Я помогу диагностировать проблему!

---

**Статус:** ✅ Готово к развёртыванию!
