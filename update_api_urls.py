#!/usr/bin/env python3
"""
Утилита для обновления URL API и WebSocket в HTML файлах
Использование: python update_api_urls.py https://your-server.com
"""

import sys
import re
from pathlib import Path

def update_html_urls(api_base: str, ws_url: str):
    """Обновляет URLs в HTML файлах"""
    
    # Путь к папке с шаблонами (относительно корня проекта)
    templates_dir = Path(__file__).parent / "cyber-vis" / "src" / "cyber_vis" / "app" / "templates"
    
    if not templates_dir.exists():
        print(f"❌ Папка {templates_dir} не найдена!")
        return False
    
    script_config = f"""        <script>
            // Конфигурация подключения к API
            window.CYBER_VIS_API_BASE = '{api_base}';
            window.CYBER_VIS_WS_URL = '{ws_url}';
        </script>
"""
    
    files_to_update = ["index.html", "monitor.html"]
    
    for filename in files_to_update:
        filepath = templates_dir / filename
        
        if not filepath.exists():
            print(f"⚠️  Файл {filepath} не найден")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем тег <head>
        if "<head>" not in content:
            print(f"❌ Тег <head> не найден в {filename}")
            continue
        
        # Удаляем старый скрипт конфигурации (если есть)
        content = re.sub(
            r'        <script>\s*// Конфигурация подключения.*?</script>\s*\n',
            '',
            content,
            flags=re.DOTALL
        )
        
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
        print("Использование: python update_api_urls.py <API_URL>")
        print("Пример: python update_api_urls.py https://diplom-cyber-security.onrender.com")
        sys.exit(1)
    
    api_url = sys.argv[1].rstrip('/')
    ws_url = api_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/monitor'
    
    print(f"🔄 Обновляю HTML файлы...")
    print(f"   API Base: {api_url}")
    print(f"   WebSocket: {ws_url}")
    print()
    
    if update_html_urls(api_url, ws_url):
        print("\n✅ Готово! API и WebSocket URL обновлены в HTML файлах.")
    else:
        print("\n❌ Ошибка при обновлении файлов.")
        sys.exit(1)
