#!/usr/bin/env python3
"""
Утилита для обновления URL API и WebSocket в HTML файлах.

Использование:
  python update_api_urls.py <API_URL> [TEMPLATES_DIR]

Пример (шаблоны в репозитории):
  python update_api_urls.py https://your-server.com

Пример (любой другой сайт, например GitHub Pages):
  python update_api_urls.py https://your-server.com "D:\\path\\to\\site"
"""

import sys
import re
from pathlib import Path

def _configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream and hasattr(stream, "reconfigure"):
                stream.reconfigure(errors="replace")
        except Exception:
            pass

def update_html_urls(api_base: str, ws_url: str, templates_dir: Path) -> bool:
    """Обновляет URLs в HTML файлах"""
    
    if not templates_dir.exists():
        print(f"[ERROR] Folder not found: {templates_dir}")
        return False
    
    script_config = f"""    <script>
        // Конфигурация подключения к API
        window.CYBER_VIS_API_BASE = '{api_base}';
        window.CYBER_VIS_WS_URL = '{ws_url}';
    </script>
"""

    config_script_pattern = re.compile(
        r"<script[^>]*>.*?window\\.CYBER_VIS_API_BASE\\s*=.*?window\\.CYBER_VIS_WS_URL\\s*=.*?</script>\\s*",
        flags=re.DOTALL | re.IGNORECASE,
    )
    
    files_to_update = ["index.html", "monitor.html"]
    updated_any = False
    
    for filename in files_to_update:
        filepath = templates_dir / filename
        
        if not filepath.exists():
            print(f"[WARN] File not found: {filepath}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Удаляем старый конфиг (если есть)
        content = config_script_pattern.sub("", content)

        # Вставляем новый конфиг сразу после <head>
        content, count = re.subn(
            r"(<head[^>]*>)",
            r"\\1\n" + script_config,
            content,
            count=1,
            flags=re.IGNORECASE,
        )
        if count == 0:
            print(f"[ERROR] <head> tag not found in {filename}")
            continue
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        updated_any = True
        print(f"[OK] {filename} updated: API_BASE = {api_base}, WS_URL = {ws_url}")
    
    return updated_any

if __name__ == "__main__":
    _configure_stdout()

    if len(sys.argv) < 2:
        print("Usage: python update_api_urls.py <API_URL> [TEMPLATES_DIR]")
        print("Example: python update_api_urls.py https://your-server.com")
        sys.exit(1)
    
    api_url = sys.argv[1].rstrip('/')
    ws_url = api_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/monitor'

    default_templates_dir = Path(__file__).parent / "cyber-vis" / "src" / "cyber_vis" / "app" / "templates"
    templates_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else default_templates_dir
    
    print("Updating HTML files...")
    print(f"  templates_dir: {templates_dir}")
    print(f"  API Base: {api_url}")
    print(f"  WebSocket: {ws_url}")
    print()
    
    if update_html_urls(api_url, ws_url, templates_dir=templates_dir):
        print("\nDone. API and WebSocket URL updated in HTML files.")
    else:
        print("\nError: failed to update HTML files.")
        sys.exit(1)
