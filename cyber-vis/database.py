import sqlite3
import json
from datetime import datetime

class LoginDatabase:
    """База данных для хранения попыток входа"""
    
    def __init__(self, db_path="login_attempts.db"):
        self.db_path = db_path
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
                    client_type TEXT,
                    success BOOLEAN NOT NULL,
                    reason TEXT,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    metadata TEXT
                )
            ''')
            conn.commit()
    
    def add_attempt(self, username, ip_address, client_type, success, reason="", user_agent="", metadata=None):
        """Добавить попытку входа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO login_attempts 
                (username, ip_address, client_type, success, reason, user_agent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                ip_address,
                client_type,
                success,
                reason,
                user_agent,
                json.dumps(metadata) if metadata else None
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
    
    def get_stats(self):
        """Получить статистику"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
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
            
            # Попытки за последний час
            cursor.execute('''
                SELECT COUNT(*) as last_hour
                FROM login_attempts 
                WHERE datetime(attempt_time) > datetime('now', '-1 hour')
            ''')
            last_hour = cursor.fetchone()[0] or 0
            
            return {
                'total_attempts': row[0] or 0,
                'successful': row[1] or 0,
                'failed': row[2] or 0,
                'unique_users': row[3] or 0,
                'unique_ips': row[4] or 0,
                'last_hour': last_hour
            }

# Глобальный экземпляр БД
db = LoginDatabase()