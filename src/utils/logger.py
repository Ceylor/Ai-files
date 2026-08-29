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
        
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Отключает WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Remaining: {len(self.active_connections)}")
    
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
        except Exception:
            self.disconnect(websocket)

# Глобальный экземпляр
ws_manager = ConnectionManager()

class BatchConnectionManager:
    """Управляет WebSocket подключениями для конкретных задач (batch_id)."""
    
    def __init__(self):
        self._connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: int):
        await websocket.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, task_id: int):
        if task_id in self._connections:
            self._connections[task_id] = [
                ws for ws in self._connections[task_id] if ws != websocket
            ]
            if not self._connections[task_id]:
                del self._connections[task_id]
    
    async def send_to_task(self, task_id: int, message: str):
        """Отправляет сообщение всем клиентам, следящим за задачей."""
        if task_id not in self._connections:
            return
        disconnected = []
        for ws in self._connections[task_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws, task_id)
    
    def has_listeners(self, task_id: int) -> bool:
        return bool(self._connections.get(task_id))

batch_ws_manager = BatchConnectionManager()
