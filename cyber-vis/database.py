import os
import sqlite3
import json
from datetime import datetime, timedelta

class LoginDatabase:
    """База данных для хранения попыток входа"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.environ.get("CYBER_VIS_DB_PATH") or "login_attempts.db"
        self.init_database()
        
    def init_database(self):
        """Инициализация таблицы попыток входа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ip_address TEXT,
                    country TEXT,
                    client_type TEXT,
                    success BOOLEAN NOT NULL,
                    reason TEXT,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    metadata TEXT
                )
            ''')
            conn.commit()
            
            # Добавляем поле country к существующей таблице (если его еще нет)
            try:
                cursor.execute('ALTER TABLE login_attempts ADD COLUMN country TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Поле уже существует
                pass
            
            # Таблица заблокированных IP адресов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT UNIQUE NOT NULL,
                    reason TEXT,
                    blocked_until TIMESTAMP,
                    is_permanent BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def add_attempt(self, username, ip_address, client_type, success, reason="", user_agent="", metadata=None, country=None):
        """Добавить попытку входа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Явно передаём текущее время вместо DEFAULT CURRENT_TIMESTAMP
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO login_attempts 
                (username, ip_address, country, client_type, success, reason, user_agent, metadata, attempt_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                ip_address,
                country,
                client_type,
                int(success),  # Явно конвертируем bool в int для SQLite
                reason,
                user_agent,
                json.dumps(metadata) if metadata else None,
                current_time
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_attempts(self, limit=100):
        """Получить последние попытки входа"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM login_attempts 
                ORDER BY attempt_time DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # В методе get_stats класса LoginDatabase:
    def get_stats(self):
        """Получить статистику"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Основная статистика
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    COUNT(DISTINCT username) as unique_users,
                    COUNT(DISTINCT ip_address) as unique_ips
                FROM login_attempts
            ''')
            row = cursor.fetchone()
            
            # Попытки за последний час (динамически считаем каждый раз)
            cursor.execute('''
                SELECT COUNT(*) as last_hour
                FROM login_attempts 
                WHERE datetime(attempt_time) > datetime('now', '-1 hour')
            ''')
            last_hour_row = cursor.fetchone()
            last_hour = last_hour_row[0] if last_hour_row else 0
            
            # Попытки за последние 30 минут
            cursor.execute('''
                SELECT COUNT(*) as last_30_min
                FROM login_attempts 
                WHERE datetime(attempt_time) > datetime('now', '-30 minutes')
            ''')
            last_30_min_row = cursor.fetchone()
            last_30_min = last_30_min_row[0] if last_30_min_row else 0
            
            # Попытки за последние 10 минут
            cursor.execute('''
                SELECT COUNT(*) as last_10_min
                FROM login_attempts 
                WHERE datetime(attempt_time) > datetime('now', '-10 minutes')
            ''')
            last_10_min_row = cursor.fetchone()
            last_10_min = last_10_min_row[0] if last_10_min_row else 0
            
            return {
                'total_attempts': row[0] or 0,
                'successful': row[1] or 0,
                'failed': row[2] or 0,
                'unique_users': row[3] or 0,
                'unique_ips': row[4] or 0,
                'last_hour': last_hour,
                'last_30_min': last_30_min,
                'last_10_min': last_10_min,
                'timestamp': datetime.now().isoformat()  # Добавляем метку времени
            }
    
    def get_failed_attempts_count(self, ip_address: str, minutes: int = 15) -> int:
        """Получить количество неудачных попыток за последние N минут"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            time_threshold = datetime.now() - timedelta(minutes=minutes)
            time_threshold_iso = time_threshold.isoformat()
            
            # DEBUG: Проверяем, что вообще есть в БД
            cursor.execute('SELECT COUNT(*) FROM login_attempts WHERE ip_address = ?', (ip_address,))
            total_for_ip = cursor.fetchone()[0]
            
            # DEBUG: Проверяем значения success
            cursor.execute('SELECT success, COUNT(*) FROM login_attempts WHERE ip_address = ? GROUP BY success', (ip_address,))
            success_stats = cursor.fetchall()
            
            print(f"   🔍 DEBUG get_failed_attempts: IP={ip_address}, всего попыток={total_for_ip}, статусы={success_stats}")
            
            # Исправленный запрос - используем >= для строкового сравнения ISO format
            cursor.execute('''
                SELECT COUNT(*) FROM login_attempts 
                WHERE ip_address = ? AND success = 0 AND attempt_time >= ?
            ''', (ip_address, time_threshold_iso))
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            print(f"   🔍 DEBUG: Неудачных за {minutes} мин: {count}, порог времени: {time_threshold_iso}")
            
            return count
    
    def add_ip_block(self, ip_address: str, reason: str, duration_minutes: int = None, is_permanent: bool = False) -> bool:
        """Добавить IP в блокировку"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            blocked_until = None
            if not is_permanent and duration_minutes:
                blocked_until = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO ip_blocks 
                    (ip_address, reason, blocked_until, is_permanent)
                    VALUES (?, ?, ?, ?)
                ''', (ip_address, reason, blocked_until, is_permanent))
                conn.commit()
                return True
            except Exception as e:
                print(f"❌ Ошибка добавления блокировки IP: {e}")
                return False
    
    def is_ip_blocked(self, ip_address: str) -> tuple:
        """Проверить, заблокирован ли IP. Возвращает (is_blocked, reason)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT reason, blocked_until, is_permanent FROM ip_blocks 
                WHERE ip_address = ?
            ''', (ip_address,))
            result = cursor.fetchone()
            
            if not result:
                return False, None
            
            reason, blocked_until, is_permanent = result
            
            # Если постоянная блокировка
            if is_permanent:
                return True, f"🚫 Постоянная блокировка: {reason}"
            
            # Если временная блокировка
            if blocked_until:
                blocked_until_dt = datetime.fromisoformat(blocked_until)
                if datetime.now() < blocked_until_dt:
                    remaining = blocked_until_dt - datetime.now()
                    minutes = int(remaining.total_seconds() / 60)
                    return True, f"⏱️ IP заблокирован на {minutes} мин: {reason}"
                else:
                    # Истекла временная блокировка, удаляем
                    cursor.execute('DELETE FROM ip_blocks WHERE ip_address = ?', (ip_address,))
                    conn.commit()
                    return False, None
            
            return False, None
    
    def get_blocked_ips(self) -> list:
        """Получить список всех заблокированных IP"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Сначала удаляем истёкшие временные блокировки
            cursor.execute('''
                DELETE FROM ip_blocks 
                WHERE is_permanent = 0 AND blocked_until < ?
            ''', (datetime.now().isoformat(),))
            conn.commit()
            
            # Получаем оставшиеся блокировки
            cursor.execute('''
                SELECT * FROM ip_blocks ORDER BY created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

# Глобальный экземпляр БД
db = LoginDatabase()
