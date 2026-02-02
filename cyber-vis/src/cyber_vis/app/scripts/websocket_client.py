"""
Простой WebSocket клиент для cyber-vis
"""
import asyncio
import websockets
import json

class SimpleWebSocketClient:
    def __init__(self, server_url="ws://localhost:8765"):
        """
        Инициализация WebSocket клиента
        
        Args:
            server_url (str): URL WebSocket сервера
        """
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        
    async def connect(self):
        """Подключение к WebSocket серверу"""
        try:
            print(f"🔄 Подключаюсь к {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            print("✅ Подключение успешно!")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    async def authenticate(self, username, password):
        """Аутентификация на сервере"""
        if not self.connected:
            return None
            
        auth_data = {
            "username": username,
            "password": password
        }
        
        return await self.send_message(json.dumps(auth_data))
    
    async def send_message(self, message):
        """Отправка сообщения"""
        if not self.connected or not self.websocket:
            print("⚠️ Не подключено к серверу")
            return None
            
        try:
            await self.websocket.send(message)
            print(f"📤 Отправлено: {message}")
            
            # Ждем ответ
            response = await self.websocket.recv()
            print(f"📥 Получено: {response}")
            return response
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return None
    
    async def listen_for_messages(self):
        """Прослушивание сообщений от сервера"""
        if not self.connected or not self.websocket:
            print("⚠️ Не подключено к серверу")
            return
            
        try:
            print("🎧 Начало прослушивания сообщений...")
            async for message in self.websocket:
                print(f"📨 Новое сообщение: {message}")
                # Здесь можно обрабатывать сообщения
                
        except websockets.exceptions.ConnectionClosed:
            print("📴 Соединение закрыто")
            self.connected = False
    
    async def disconnect(self):
        """Отключение от сервера"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("🔌 Отключено от сервера")
    
    async def simple_test(self):
        """Простой тест подключения и отправки сообщения"""
        connected = await self.connect()
        if connected:
            # Отправляем тестовое сообщение
            response = await self.send_message("Hello WebSocket!")
            
            # Закрываем соединение
            await self.disconnect()
            return response
        return None


# Пример использования
async def test_websocket_async():
    """Тестирование WebSocket клиента"""
    # Используем тестовый сервер (можно заменить на свой)
    client = SimpleWebSocketClient("wss://echo.websocket.org")
    
    # Подключаемся
    if await client.connect():
        # Отправляем сообщение
        response = await client.send_message("Привет от cyber-vis!")
        print(f"Ответ сервера: {response}")
        
        # Закрываем соединение
        await client.disconnect()


# ДОБАВИТЬ в КОНЕЦ файла:
def test_websocket():
    """Функция для тестирования WebSocket"""
    import asyncio
    asyncio.run(test_websocket_async())


# Для запуска из командной строки
if __name__ == "__main__":
    asyncio.run(test_websocket())