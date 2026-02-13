#!/usr/bin/env python3
"""
Утилита для обновления URL API и WebSocket в HTML файлах.
Использование: python3 update_api_urls.py https://your-server.com "/path/to/site"
"""

import sys
import re
from pathlib import Path
from typing import Optional

CONFIG_SCRIPT_PATTERN = re.compile(
    r"<script>.*?CYBER_VIS_API_BASE.*?</script>\s*",
    flags=re.DOTALL | re.IGNORECASE,
)

def resolve_site_dir(path_arg: Optional[str]) -> Optional[Path]:
    if path_arg:
        site_dir = Path(path_arg)
    else:
        site_dir = Path.cwd()

    if not site_dir.exists() or not site_dir.is_dir():
        print(f"❌ Папка сайта не найдена: {site_dir}")
        return None

    if not (site_dir / "index.html").exists() and not (site_dir / "monitor.html").exists():
        print(f"❌ В папке нет index.html или monitor.html: {site_dir}")
        return None

    return site_dir

def update_html_urls(api_base: str, ws_url: str, site_dir: Path):
    """Обновляет URLs в HTML файлах"""
    
    script_config = f"""        <script>
            // Конфигурация подключения к API
            window.CYBER_VIS_API_BASE = '{api_base}';
            window.CYBER_VIS_WS_URL = '{ws_url}';
        </script>
"""
    
    files_to_update = ["index.html", "monitor.html"]
    
    for filename in files_to_update:
        filepath = site_dir / filename
        
        if not filepath.exists():
            print(f"⚠️  Файл {filepath} не найден")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        content = re.sub(r"^\s*\\1\s*$", "", content, flags=re.MULTILINE)
        content = re.sub(CONFIG_SCRIPT_PATTERN, "", content)

        if "<head>" not in content:
            content = re.sub(r"(<html[^>]*>)", r"\\1\n<head>", content, count=1, flags=re.IGNORECASE)
        
        # Ищем тег <head>
        if "<head>" not in content:
            print(f"❌ Тег <head> не найден в {filename}")
            continue
        
        # Вставляем новый скрипт после <head>
        content = content.replace(
            "<head>",
            f"<head>\n{script_config}",
            1
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filename} обновлён: API_BASE = {api_base}, WS_URL = {ws_url}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 update_api_urls.py <API_URL> \"/path/to/site\"")
        print("Пример: python3 update_api_urls.py https://api.example.com \"/var/www/site\"")
        sys.exit(1)
    
    api_url = sys.argv[1].rstrip('/')
    ws_url = api_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/monitor'
    site_dir = resolve_site_dir(sys.argv[2] if len(sys.argv) > 2 else None)
    
    if not site_dir:
        sys.exit(1)
    
    print("🔄 Обновляю HTML файлы...")
    print(f"   API Base: {api_url}")
    print(f"   WebSocket: {ws_url}")
    print(f"   Site dir: {site_dir}")
    print()
    
    if update_html_urls(api_url, ws_url, site_dir):
        print("\n✅ Готово! API и WebSocket URL обновлены в HTML файлах.")
    else:
        print("\n❌ Ошибка при обновлении файлов.")
        sys.exit(1)
