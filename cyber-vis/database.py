import psycopg2
import psycopg2.extras
from psycopg2 import sql
import json
import os
from datetime import datetime, timedelta

class LoginDatabase:
    """База данных для хранения попыток входа на PostgreSQL"""
    
    def __init__(self, database_url=None):
        if database_url is None:
            database_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/login_monitor')
        self.database_url = database_url
        self.init_database()
        
    def init_database(self):
        """Инициализация таблиц на PostgreSQL"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Таблица попыток входа
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    ip_address TEXT,
                    country TEXT,
                    client_type TEXT,
                    success BOOLEAN NOT NULL,
                    reason TEXT,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    metadata JSONB
                )
            ''')
            
            # Таблица заблокированных IP
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_blocks (
                    id SERIAL PRIMARY KEY,
                    ip_address TEXT UNIQUE NOT NULL,
                    reason TEXT,
                    blocked_until TIMESTAMP,
                    is_permanent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индексы для производительности
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_address 
                ON login_attempts(ip_address)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_login_attempts_attempt_time 
                ON login_attempts(attempt_time)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ip_blocks_ip_address 
                ON ip_blocks(ip_address)
            ''')
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ База данных PostgreSQL инициализирована")
        except psycopg2.Error as e:
            print(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    def add_attempt(self, username, ip_address, client_type, success, reason="", user_agent="", metadata=None, country=None):
        """Добавить попытку входа"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO login_attempts 
                (username, ip_address, country, client_type, success, reason, user_agent, metadata, attempt_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                username,
                ip_address,
                country,
                client_type,
                success,
                reason,
                user_agent,
                json.dumps(metadata) if metadata else None,
                current_time
            ))
            attempt_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return attempt_id
        except psycopg2.Error as e:
            print(f"❌ Ошибка добавления попытки входа: {e}")
            return None
    
    def _connect(self):
        """Создать подключение к PostgreSQL."""
        return psycopg2.connect(self.database_url)

    def _jsonify_metadata(self, row_dict: dict) -> dict:
        """Привести metadata к обычному dict (psycopg2 может вернуть строку/объект)."""
        if not row_dict:
            return row_dict
        md = row_dict.get("metadata")
        if isinstance(md, str):
            try:
                row_dict["metadata"] = json.loads(md)
            except Exception:
                pass
        return row_dict

    def get_attempt_by_id(self, attempt_id: int) -> dict | None:
        """Получить попытку входа по ID."""
        try:
            conn = self._connect()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT id, username, ip_address, country, client_type, success, reason,
                       attempt_time, user_agent, metadata
                FROM login_attempts
                WHERE id = %s
            ''', (attempt_id,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return None
            return self._jsonify_metadata(dict(row))
        except psycopg2.Error as e:
            print(f"❌ Ошибка получения попытки по id={attempt_id}: {e}")
            return None

    def get_recent_attempts(self, limit=100):
        """Получить последние попытки входа"""
        try:
            conn = self._connect()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT id, username, ip_address, country, client_type, success, reason,
                       attempt_time, user_agent, metadata
                FROM login_attempts
                ORDER BY attempt_time DESC
                LIMIT %s
            ''', (limit,))

            results = [self._jsonify_metadata(dict(row)) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return results
        except psycopg2.Error as e:
            print(f"❌ Ошибка получения попыток входа: {e}")
            return []
    
    def get_stats(self):
        """Получить статистику"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Основная статистика
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed,
                    COUNT(DISTINCT username) as unique_users,
                    COUNT(DISTINCT ip_address) as unique_ips
                FROM login_attempts
            ''')
            row = cursor.fetchone()
            
            # Попытки за последний час
            cursor.execute('''
                SELECT COUNT(*) as last_hour
                FROM login_attempts 
                WHERE attempt_time > NOW() - INTERVAL '1 hour'
            ''')
            last_hour = cursor.fetchone()[0] or 0
            
            # Попытки за последние 30 минут
            cursor.execute('''
                SELECT COUNT(*) as last_30_min
                FROM login_attempts 
                WHERE attempt_time > NOW() - INTERVAL '30 minutes'
            ''')
            last_30_min = cursor.fetchone()[0] or 0
            
            # Попытки за последние 10 минут
            cursor.execute('''
                SELECT COUNT(*) as last_10_min
                FROM login_attempts 
                WHERE attempt_time > NOW() - INTERVAL '10 minutes'
            ''')
            last_10_min = cursor.fetchone()[0] or 0
            
            cursor.close()
            conn.close()
            
            return {
                'total_attempts': row[0] or 0,
                'successful': row[1] or 0,
                'failed': row[2] or 0,
                'unique_users': row[3] or 0,
                'unique_ips': row[4] or 0,
                'last_hour': last_hour,
                'last_30_min': last_30_min,
                'last_10_min': last_10_min,
                'timestamp': datetime.now().isoformat()
            }
        except psycopg2.Error as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_attempts': 0,
                'successful': 0,
                'failed': 0,
                'unique_users': 0,
                'unique_ips': 0,
                'last_hour': 0,
                'last_30_min': 0,
                'last_10_min': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_failed_attempts_count(self, ip_address: str, minutes: int = 15) -> int:
        """Получить количество неудачных попыток за последние N минут"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            time_threshold = datetime.now() - timedelta(minutes=minutes)
            
            cursor.execute('''
                SELECT COUNT(*) FROM login_attempts 
                WHERE ip_address = %s AND success = false AND attempt_time >= %s
            ''', (ip_address, time_threshold))
            
            count = cursor.fetchone()[0] or 0
            cursor.close()
            conn.close()
            return count
        except psycopg2.Error as e:
            print(f"❌ Ошибка подсчёта неудачных попыток: {e}")
            return 0
    
    def add_ip_block(self, ip_address: str, reason: str, duration_minutes: int = None, is_permanent: bool = False) -> bool:
        """Добавить IP в блокировку"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            blocked_until = None
            if not is_permanent and duration_minutes:
                blocked_until = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
            
            cursor.execute('''
                INSERT INTO ip_blocks 
                (ip_address, reason, blocked_until, is_permanent)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ip_address) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    blocked_until = EXCLUDED.blocked_until,
                    is_permanent = EXCLUDED.is_permanent
            ''', (ip_address, reason, blocked_until, is_permanent))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except psycopg2.Error as e:
            print(f"❌ Ошибка добавления блокировки IP: {e}")
            return False
    
    def is_ip_blocked(self, ip_address: str) -> tuple:
        """Проверить, заблокирован ли IP. Возвращает (is_blocked, reason)"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT reason, blocked_until, is_permanent FROM ip_blocks 
                WHERE ip_address = %s
            ''', (ip_address,))
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                conn.close()
                return False, None
            
            reason, blocked_until, is_permanent = result
            
            # Если постоянная блокировка
            if is_permanent:
                cursor.close()
                conn.close()
                return True, f"🚫 Постоянная блокировка: {reason}"
            
            # Если временная блокировка
            if blocked_until:
                if datetime.now() < blocked_until:
                    remaining = blocked_until - datetime.now()
                    minutes = int(remaining.total_seconds() / 60)
                    cursor.close()
                    conn.close()
                    return True, f"⏱️ IP заблокирован на {minutes} мин: {reason}"
                else:
                    # Истекла временная блокировка, удаляем
                    cursor.execute('DELETE FROM ip_blocks WHERE ip_address = %s', (ip_address,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return False, None
            
            cursor.close()
            conn.close()
            return False, None
        except psycopg2.Error as e:
            print(f"❌ Ошибка проверки блокировки IP: {e}")
            return False, None
    
    def get_blocked_ips(self) -> list:
        """Получить список всех заблокированных IP"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Сначала удаляем истёкшие временные блокировки
            cursor.execute('''
                DELETE FROM ip_blocks 
                WHERE is_permanent = false AND blocked_until < NOW()
            ''')
            conn.commit()
            
            # Получаем оставшиеся блокировки
            cursor.execute('''
                SELECT id, ip_address, reason, blocked_until, is_permanent, created_at
                FROM ip_blocks 
                ORDER BY created_at DESC
            ''')
            
            columns = ['id', 'ip_address', 'reason', 'blocked_until', 'is_permanent', 'created_at']
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return results
        except psycopg2.Error as e:
            print(f"❌ Ошибка получения заблокированных IP: {e}")
            return []

# Глобальный экземпляр БД
db = LoginDatabase()