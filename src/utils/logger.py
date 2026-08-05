"""
Менеджер WebSocket для передачи логов в реальном времени
"""
from fastapi import WebSocket
from typing import List
from collections import deque
from datetime import datetime

class ConnectionManager:
    """Управляет WebSocket соединениями с клиентами"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.log_buffer: deque = deque(maxlen=100)
    
    async def connect(self, websocket: WebSocket):
        """Подключает новый WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Отправляем буфер логов новому клиенту
        for log in list(self.log_buffer)[-20:]:  # Последние 20 логов
            try:
                await websocket.send_text(log)
            except Exception:
                pass
        
        print(f" Клиент подключился. Всего клиентов: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Отключает WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"📴 Клиент отключился. Осталось клиентов: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        """
        Отправляет сообщение всем подключенным клиентам
        
        Args:
            message: Текст сообщения для отправки
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Добавляем в буфер (deque автоматически ограничивает размер)
        self.log_buffer.append(formatted_message)
        
        # Отправляем всем клиентам
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(formatted_message)
            except Exception:
                # Клиент отключился
                disconnected.append(connection)
        
        # Удаляем отключенных клиентов
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_client(self, websocket: WebSocket, message: str):
        """Отправляет сообщение конкретному клиенту"""
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

# Глобальный экземпляр
ws_manager = ConnectionManager()