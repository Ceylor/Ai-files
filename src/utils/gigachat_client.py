"""
GigaChat API Client
Интеграция с облачным AI от Сбера как fallback для локальной Ollama
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from src.utils.logger import ws_manager

class GigaChatClient:
    """Клиент для работы с GigaChat API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config["cloud_fallback"]
        self.base_url = "https://api.giga.chat/v1"
        self.oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        
        # Read credentials from environment variables
        self.client_id = os.environ.get(self.config.get("client_id_env", "GIGACHAT_CLIENT_ID"), "")
        self.scope = self.config.get("scope", "GIGACHAT_API_PERS")
        self.auth_key = os.environ.get(self.config.get("authorization_key_env", "GIGACHAT_AUTH_KEY"), "")
        self.model = self.config.get("model", "GigaChat-2-Max")
        
        self.access_token = None
        self.token_expires_at = 0
        self.token_cache_file = Path(self.config.get("token_cache_file", "./data/temp/gigachat_token.json"))
    
    async def get_access_token(self) -> Optional[str]:
        """Получает или обновляет Access Token"""
        
        # Проверяем кэш
        if self._is_token_valid():
            return self.access_token
        
        await ws_manager.broadcast("🔄 Получение токена GigaChat...")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.oauth_url,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "Authorization": f"Basic {self.auth_key}"
                    },
                    data={
                        "scope": self.scope
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 1800)  # 30 минут по умолчанию
                    self.token_expires_at = time.time() + expires_in - 300  # Обновляем за 5 мин до истечения
                    
                    # Сохраняем в кэш
                    self._save_token_to_cache()
                    
                    await ws_manager.broadcast("✅ Токен GigaChat получен")
                    return self.access_token
                else:
                    await ws_manager.broadcast(f"❌ Ошибка получения токена: {response.status_code}")
                    return None
                    
        except Exception as e:
            await ws_manager.broadcast(f"❌ Ошибка подключения к GigaChat: {e}")
            return None
    
    def _is_token_valid(self) -> bool:
        """Проверяет, действителен ли токен"""
        if not self.access_token:
            return False
        return time.time() < self.token_expires_at
    
    def _save_token_to_cache(self):
        """Сохраняет токен в файл для быстрого доступа"""
        try:
            self.token_cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "access_token": self.access_token,
                "expires_at": self.token_expires_at
            }
            with open(self.token_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)
        except Exception:
            pass  # Игнорируем ошибки кэширования
    
    def _load_token_from_cache(self):
        """Загружает токен из файла"""
        try:
            if self.token_cache_file.exists():
                with open(self.token_cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self.access_token = cache_data.get("access_token")
                    self.token_expires_at = cache_data.get("expires_at", 0)
        except Exception:
            pass
    
    async def generate_response(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """
        Отправляет промпт в GigaChat и получает ответ
        
        Args:
            prompt: Текст промпта
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            Текст ответа или None
        """
        # Загружаем токен из кэша при первом вызове
        if not self.access_token:
            self._load_token_from_cache()
        
        # Получаем токен (из кэша или новый)
        token = await self.get_access_token()
        if not token:
            return None
        
        await ws_manager.broadcast("🧠 Отправка запроса в GigaChat...")
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Ты - профессиональный AI-режиссер монтажа видео. Твоя задача - анализировать видео и создавать структурированные планы монтажа."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    await ws_manager.broadcast("✅ Ответ от GigaChat получен")
                    return answer
                else:
                    await ws_manager.broadcast(f"❌ Ошибка GigaChat API: {response.status_code}")
                    if response.status_code == 401:
                        # Токен истек, очищаем кэш
                        self.access_token = None
                        self.token_expires_at = 0
                        if self.token_cache_file.exists():
                            self.token_cache_file.unlink()
                    return None
                    
        except httpx.TimeoutException:
            await ws_manager.broadcast("️ Превышено время ожидания ответа от GigaChat")
            return None
        except Exception as e:
            await ws_manager.broadcast(f"❌ Ошибка запроса к GigaChat: {e}")
            return None
    
    async def analyze_video_cluster(self, videos_metadata: list) -> Optional[List[Dict[str, Any]]]:
        """
        Специализированный метод для анализа и группировки видео
        
        Args:
            videos_metadata: Список метаданных видео
            
        Returns:
            Структура кластеров или None
        """
        prompt = self._create_clustering_prompt(videos_metadata)
        
        response_text = await self.generate_response(prompt, max_tokens=3000)
        
        if not response_text:
            return None
        
        # Парсим JSON из ответа
        try:
            # Ищем JSON в ответе
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                return data.get("clusters", [])
        except json.JSONDecodeError as e:
            await ws_manager.broadcast(f"️  Ошибка парсинга JSON от GigaChat: {e}")
            return None
        
        return None
    
    def _create_clustering_prompt(self, videos_metadata: list) -> str:
        """Создает промпт для группировки видео"""
        
        prompt = """Ты - профессиональный AI-режиссер монтажа. 
Твоя задача - сгруппировать видеофрагменты в логически завершенные короткие видео (Shorts 9:16).

У тебя есть следующие видеофрагменты:

"""
        
        for i, video in enumerate(videos_metadata, 1):
            prompt += f"""
Фрагмент {i}:
- Файл: {video.get('filename', 'unknown')}
- Длительность: {video.get('duration', 0):.1f} сек
- Настроение: {video.get('mood', 'unknown')}
- Сцен: {video.get('scenes', 0)}
- Транскрипция: {video.get('transcript', 'нет текста')[:300]}
"""
        
        prompt += """
ИНСТРУКЦИЯ:
1. Проанализируй все фрагменты
2. Сгруппируй их в 1-5 логически завершенных клипов
3. Для каждого клипа укажи:
   - Название (краткое, привлекательное)
   - Список номеров фрагментов (indices)
   - Общее настроение (mood): energetic, calm, epic, funny
   - Примерную длительность
   - Hook (цепляющее начало) - какой фрагмент поставить первым

ВЕРНИ СТРОГО JSON в формате:
{
  "clusters": [
    {
      "title": "Название клипа",
      "fragment_indices": [1, 3, 5],
      "mood": "energetic",
      "estimated_duration": 45,
      "hook_fragment": 1,
      "description": "Краткое описание"
    }
  ]
}

Отвечай ТОЛЬКО JSON, без дополнительных комментариев."""
        
        return prompt
    
    async def analyze_story_structure(self, fragments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Специализированный метод для построения нарративной структуры
        
        Args:
            fragments: Список фрагментов с метаданными
            
        Returns:
            Структура истории или None
        """
        prompt = self._create_story_structure_prompt(fragments)
        
        response_text = await self.generate_response(prompt, max_tokens=4000)
        
        if not response_text:
            return None
        
        # Парсим JSON из ответа
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                return data
        except json.JSONDecodeError as e:
            await ws_manager.broadcast(f"Ошибка парсинга JSON от GigaChat: {e}")
            return None
        
        return None
    
    def _create_story_structure_prompt(self, fragments: List[Dict[str, Any]]) -> str:
        """Создает промпт для построения нарративной структуры"""
        
        prompt = """Ты - профессиональный AI-режиссер монтажа. Твоя задача - создать ВИРУАЛЬНЫЙ клип из набора видеофрагментов.

У тебя есть следующие фрагменты:
"""
        
        for i, frag in enumerate(fragments, 1):
            # A7 FIX: transcript — это List[Dict], нужно правильно преобразовать в строку
            transcript_data = frag.get("transcript", [])
            if isinstance(transcript_data, list):
                text = " ".join(seg.get("text", "") for seg in transcript_data[:5] if isinstance(seg, dict) and seg.get("text"))
            else:
                text = str(transcript_data) if transcript_data else ""
            
            prompt += f"""
--- Фрагмент {i} ---
- Файл: {frag.get('filename', 'unknown')}
- Длительность: {frag.get('duration', 0):.1f} сек
- Транскрипция: {text.strip()[:300]}
- Сцены: {frag.get('scenes', 0)}
- Настроение: {frag.get('mood', 'unknown')}
- Аудиоэнергия: {frag.get('audio_energy', 'unknown')}
"""
        
        prompt += """
ТВОИ ЗАДАЧИ:

1. ОПРЕДЕЛИ ТИП ИСТОРИИ (выбери ОДИН):
   - "journey" = Путешествие/Приключение (сборы → дорога → прибытие)
   - "before_after" = До/После (проблема → решение)
   - "tutorial" = Туториал (проблема → шаги → результат)
   - "reaction" = Реакция/Эмоция (контекст → шок → последствия)

2. ОПРЕДЕЛИ ЛОГИЧЕСКУЮ ЦЕПОЧКУ:
   Для каждого фрагмента укажи его роль:
   - "hook" = САМЫЙ ЯРКИЙ момент (для начала клипа!)
   - "preparation" = Сборы, планы, начало
   - "journey" = Процесс, дорога, действие
   - "obstacle" = Проблема, препятствие
   - "solution" = Решение проблемы
   - "arrival" = Прибытие, результат
   - "celebration" = Эмоции, радость, финал
   - "before" = До изменения (скучно, обычно)
   - "transition" = Момент изменения
   - "after" = После изменения (круто, эмоционально)
   - "problem" = Что хотим сделать
   - "step1/step2/step3" = Шаги процесса
   - "result" = Итог
   - "setup" = Контекст
   - "reaction" = Эмоциональный отклик
   - "aftermath" = Последствия

3. ОТБРОСЬ "МУСОР":
   Фрагменты с низкой важностью - УДАЛИ их.

4. ОПРЕДЕЛИ ТЕМП ДЛЯ КАЖДОГО ФРАГМЕНТА:
   - "fast" = Быстрые сцены (дорога, движение)
   - "normal" = Эмоциональные сцены
   - "slow" = Скучные сцены (ускорить или удалить)

ВАЖНО:
- Hook должен быть В ПЕРВОЙ СЕКУНДЕ клипа
- Сортируй по ЛОГИКЕ, а не по времени съемки

ВЕРНИ СТРОГО JSON:
{
  "story_type": "journey",
  "story_name": "Краткое название",
  "chain": [
    {
      "fragment_index": 1,
      "role": "hook",
      "tempo": "fast",
      "keep": true
    }
  ],
  "excluded_indices": [2, 5],
  "hook_fragment": 1,
  "estimated_duration": 45
}

Отвечай ТОЛЬКО JSON, без дополнительных комментариев."""
        
        return prompt