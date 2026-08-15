"""
Story Builder - Строит смысловую историю из видеофрагментов

Использует LLM для:
1. Определения типа истории (путешествие, до/после, туториал, реакция)
2. Сортировки фрагментов по логической цепочке
3. Выбора лучшего Hook (яркий момент, не первый!)
4. Удаления "мусора" (скучные моменты)
5. Определения темпа для каждой сцены

Поддержка "золотых моментов" (модуль 8): если передан параметр golden_moments,
система предпочитает выбирать хук из топ-N самых ярких фрагментов.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from src.core.config_loader import load_config
from src.utils.logger import ws_manager


# Типы историй и их логические цепочки
STORY_TYPES = {
    "journey": {
        "name": "Путешествие/Приключение",
        "chain": ["hook", "preparation", "journey", "obstacle", "solution", "arrival", "celebration"],
        "hook_criteria": "max_emotion + visual_shock + high_audio_energy",
    },
    "before_after": {
        "name": "До/После",
        "chain": ["before", "transition", "after"],
        "hook_criteria": "max_emotion + visual_shock",
    },
    "tutorial": {
        "name": "Процесс/Туториал",
        "chain": ["problem", "step1", "step2", "step3", "result"],
        "hook_criteria": "interesting_fact + curiosity",
    },
    "reaction": {
        "name": "Реакция/Эмоция",
        "chain": ["setup", "reaction", "aftermath"],
        "hook_criteria": "emotional_peak + visual_shock",
    },
}


async def build_story(
    fragments: List[Dict[str, Any]],
    style_profile: Optional[Dict] = None,
    seed: Optional[int] = None,
    golden_moments: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Строит смысловую историю из фрагментов

    Args:
        fragments: Список фрагментов с метаданными (от LLM/ingestion)
        style_profile: Профиль стиля (vlog, cinematic и т.д.)
        seed: Seed для вариативности
        golden_moments: Список "золотых моментов" (модуль 8) для выбора хука.

    Returns:
        Dict с нарративной структурой или None при ошибке
    """
    await ws_manager.broadcast("🧠 Анализ нарративной структуры...")

    if not fragments:
        await ws_manager.broadcast("  ⚠️  Нет фрагментов для анализа")
        return None

    if seed is not None:
        import random
        random.seed(seed)
        await ws_manager.broadcast(f"  🎲 Seed для вариативности: {seed}")

    # Шаг 1: Отправляем все фрагменты в LLM для анализа
    prompt = _create_story_building_prompt(fragments, style_profile)

    config = load_config()
    provider = config["ai_brain"].get("primary_provider", "ollama")

    result = None

    if provider == "ollama":
        try:
            await ws_manager.broadcast("  📤 Отправка в Ollama для нарративного анализа...")
            result = await _send_to_llm(prompt, config, max_retries=2)
        except Exception as e:
            await ws_manager.broadcast(f"  ⚠️  Ollama не ответила: {e}")

    if not result and config["ai_brain"].get("cloud_fallback", {}).get("enabled", False):
        await ws_manager.broadcast("  🔄 Переключаюсь на GigaChat...")
        try:
            from src.utils.gigachat_client import GigaChatClient
            gigachat = GigaChatClient(config)
            result = await gigachat.analyze_story_structure(fragments)
        except Exception as e:
            await ws_manager.broadcast(f"  ⚠️  GigaChat не ответил: {e}")

    if not result:
        await ws_manager.broadcast("  🔄 Использую fallback-режим (простая сортировка)")
        result = await _fallback_story_building(fragments)

    # Применяем "золотые моменты" к выбору хука.
    result = _apply_golden_moments(result, fragments, golden_moments)

    await ws_manager.broadcast(f"  ✅ Нарративная структура построена")
    return result


def _apply_golden_moments(
    story: Dict[str, Any],
    fragments: List[Dict],
    golden_moments: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Интегрирует "золотые моменты" (модуль 8) в нарратив.

    Если golden_moments передан, переопределяет hook_fragment на самый яркий
    момент (по времени), чтобы хук открывал клип "золотым" фрагментом.

    Returns:
        Обновлённый story-словарь.
    """
    if not golden_moments:
        return story

    # Берём самый яркий золотой момент (первый в списке, т.к. они отсортированы по скору).
    top_moment = golden_moments[0]
    hook_time = float(top_moment.get("start", 0.0))

    # Находим фрагмент, содержащий этот временной диапазон.
    best_idx = None
    best_distance = float("inf")
    for frag in fragments:
        # Фрагменты могут иметь start/end или только длительность.
        frag_start = frag.get("start", 0)
        frag_dur = frag.get("duration", 0)
        frag_end = frag.get("end", frag_start + frag_dur)
        if frag_start <= hook_time <= frag_end:
            distance = min(hook_time - frag_start, frag_end - hook_time)
            if distance < best_distance:
                best_distance = distance
                best_idx = frag.get("index")

    if best_idx is not None:
        story["hook_fragment"] = best_idx
        await_marker = f"  🎯 Хук выбран из золотых моментов: фрагмент #{best_idx}"
        # Приоритет: помечаем hook в цепочке.
        for item in story.get("chain", []):
            if item.get("fragment_index") == best_idx:
                item["role"] = "hook"
                item["tempo"] = "fast"
                item["keep"] = True
        # Убеждаемся, что hook-фрагмент первый в цепочке.
        chain = story.get("chain", [])
        reordered = [i for i in chain if i.get("fragment_index") == best_idx] + \
                    [i for i in chain if i.get("fragment_index") != best_idx]
        story["chain"] = reordered
        await ws_manager.broadcast(await_marker)

    return story


def _create_story_building_prompt(fragments: List[Dict], style_profile: Optional[Dict]) -> str:
    """Создает промпт для LLM для построения нарратива"""

    prompt = """Ты - профессиональный AI-режиссер монтажа. Твоя задача - создать ВИРУАЛЬНЫЙ клип из набора видеофрагментов.

У тебя есть следующие фрагменты:
"""

    for i, frag in enumerate(fragments, 1):
        transcript_data = frag.get("transcript", [])
        if isinstance(transcript_data, list):
            text = " ".join(seg.get("text", "") for seg in transcript_data if isinstance(seg, dict) and seg.get("text"))
        else:
            text = str(transcript_data) if transcript_data else ""

        prompt += f"""
--- Фрагмент {i} ---
- Файл: {frag.get('filename', 'unknown')}
- Длительность: {frag.get('duration', 0):.1f} сек
- Транскрипция: {text[:400]}
- Сцены: {frag.get('scenes', 0)}
- Настроение: {frag.get('mood', 'unknown')}
- Аудиоэнергия: {frag.get('audio_energy', 'unknown')}
- Ключевые слова: {frag.get('keywords', [])}
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
   Фрагменты с низкой важностью (content_value="filler") и плохим качеством (visual_quality < 50) - УДАЛИ их.

4. ОПРЕДЕЛИ ТЕМП ДЛЯ КАЖДОГО ФРАГМЕНТА:
   - "fast" = Быстрые сцены (дорога, движение) → склейки каждые 0.5-1.5 сек, ускорение 1.5x
   - "normal" = Эмоциональные сцены (приехали, шок) → держим 2-4 сек, зум
   - "slow" = Скучные сцены → ускоряем 2x или вырезаем полностью

ВАЖНО:
- Hook должен быть В ПЕРВОЙ СЕКУНДЕ клипа (самый яркий кадр, не обязательно первый по времени!)
- Сортируй фрагменты ПО ЛОГИЧЕСКОЙ ЦЕПОЧКЕ, а не по времени съемки
- Удали скучные моменты (filler + low quality)

ВЕРНИ СТРОГО JSON:
{
  "story_type": "journey",
  "story_name": "Краткое название истории",
  "chain": [
    {
      "fragment_index": 1,
      "role": "hook",
      "tempo": "fast",
      "keep": true
    },
    {
      "fragment_index": 3,
      "role": "journey",
      "tempo": "normal",
      "keep": true
    }
  ],
  "excluded_indices": [2, 5],
  "hook_fragment": 1,
  "estimated_duration": 45
}

Отвечай ТОЛЬКО JSON, без дополнительных комментариев."""

    return prompt


async def _send_to_llm(prompt: str, config: Dict, max_retries: int = 2) -> Optional[Dict]:
    """Отправляет промпт в LLM и получает ответ"""
    model = config["ai_brain"]["ollama"]["model"]
    base_url = config["ai_brain"]["ollama"]["base_url"]
    timeout = config["ai_brain"]["ollama"].get("timeout", 180)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.7, "top_p": 0.9}
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("response", "")
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}") + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        data = json.loads(json_str)
                        return data
                    else:
                        raise Exception("JSON не найден в ответе")
                else:
                    raise Exception(f"LLM API error: {response.status_code}")

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    await ws_manager.broadcast(f"  ⏱️  Таймаут, попытка {attempt + 1}/{max_retries}")
                    continue
                raise Exception("Превышено время ожидания ответа от LLM")
            except httpx.ConnectError:
                raise Exception("Не удалось подключиться к Ollama")


async def _fallback_story_building(fragments: List[Dict]) -> Dict[str, Any]:
    """
    Fallback если LLM не ответил.
    Простая эвристическая сортировка с вариативностью.
    """
    await ws_manager.broadcast("  🔄 Fallback: эвристическая сортировка")
    import random

    shuffled = fragments.copy()
    random.shuffle(shuffled)
    sorted_frags = sorted(shuffled, key=lambda x: x.get("duration", 0), reverse=True)

    chain = []
    excluded = []

    for i, frag in enumerate(sorted_frags):
        role = "normal"
        tempo = "normal"
        keep = True

        if i == 0:
            role = "hook"
            tempo = "fast"
        elif i == 1 and len(sorted_frags) > 2:
            role = "preparation"
            tempo = "normal"
        elif i < len(sorted_frags) - 1:
            role = "journey"
            tempo = "normal"
        else:
            role = "result"
            tempo = "slow"

        content_value = frag.get("content_value", "")
        visual_quality = frag.get("visual_quality", 100)
        if content_value == "filler" and visual_quality < 50:
            keep = False
            excluded.append(frag.get("index", i + 1))

        chain.append({
            "fragment_index": frag.get("index", i + 1),
            "role": role,
            "tempo": tempo,
            "keep": keep
        })

    return {
        "story_type": "journey",
        "story_name": "Эвристическая история",
        "chain": chain,
        "excluded_indices": excluded,
        "hook_fragment": 1,
        "estimated_duration": min(sum(f.get("duration", 30) for f in fragments), 60)
    }


def apply_story_structure(
    fragments: List[Dict],
    story: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Применяет нарративную структуру к фрагментам:
    - Сортирует по цепочке
    - Удаляет мусор
    - Определяет темп

    Returns:
        Dict с обработанными фрагментами
    {
        "sorted_fragments": [...],
        "hook_fragment": {...},
        "scene_tempo": {...},
        "excluded": [...]
    }
    """
    chain = story.get("chain", [])
    excluded_indices = set(story.get("excluded_indices", []))

    frag_map = {f.get("index"): f for f in fragments}

    sorted_fragments = []
    scene_tempo = {}
    excluded = []

    for item in chain:
        frag_idx = item.get("fragment_index")
        if frag_idx in excluded_indices:
            excluded.append(frag_map.get(frag_idx, {}))
            continue

        if frag_idx in frag_map:
            frag = frag_map[frag_idx].copy()
            frag["role"] = item.get("role", "normal")
            frag["tempo"] = item.get("tempo", "normal")
            sorted_fragments.append(frag)
            scene_tempo[frag_idx] = item.get("tempo", "normal")

    hook_fragment = None
    for frag in sorted_fragments:
        if frag.get("role") == "hook":
            hook_fragment = frag
            break

    if not hook_fragment and sorted_fragments:
        hook_fragment = sorted_fragments[0]

    return {
        "sorted_fragments": sorted_fragments,
        "hook_fragment": hook_fragment,
        "scene_tempo": scene_tempo,
        "excluded": excluded,
        "estimated_duration": story.get("estimated_duration", 55)
    }