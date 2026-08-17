"""
Сторибилдер: построение нарративной структуры клипа.

Определяет тип истории, hook-фрагмент (цепляющее начало) и порядок
фрагментов (chain) с учётом "золотых моментов" (модуль 8) для выбора
наиболее яркого начала.

Основные функции:
    - build_story(...)         — построение нарратива (async);
    - apply_story_structure(...) — применение нарратива к фрагментам.

Контракт build_story (см. pipeline.py / processor.py):
    build_story(fragments, style_profile=None, seed=0, golden_moments=None)
        -> Dict[str, Any] | None

    Возвращает словарь вида:
        {
            "story_type": str,
            "hook_fragment": int,
            "chain": [ {"fragment_index": int, "role": str, "tempo": str, "keep": bool}, ... ],
        }

Контракт apply_story_structure (см. pipeline.py):
    apply_story_structure(fragments, story)
        -> {
            "sorted_fragments": list,
            "excluded": list,
            "scene_tempo": {fragment_index: tempo},
        }
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager


def _default_story(fragments: List[Dict], seed: int = 0) -> Dict[str, Any]:
    """Строит линейную (дефолтную) нарративную структуру по всем фрагментам."""
    chain = []
    for i, frag in enumerate(fragments):
        chain.append({
            "fragment_index": i + 1,
            "role": "hook" if i == 0 else "body",
            "tempo": "fast" if i == 0 else "normal",
            "keep": True,
        })
    return {
        "story_type": "linear",
        "hook_fragment": 1,
        "chain": chain,
    }


async def build_story(
    fragments: List[Dict],
    style_profile: Optional[Dict] = None,
    seed: int = 0,
    golden_moments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Строит нарративную структуру клипа из списка фрагментов.

    Args:
        fragments: список фрагментов (каждый — dict с ключом "index").
        style_profile: профиль стиля (необязательно).
        seed: зерно для детерминированной генерации.
        golden_moments: список "золотых моментов" (модуль 8) для выбора хука.

    Returns:
        Словарь с полями story_type, hook_fragment, chain.
    """
    await ws_manager.broadcast("  🧠 Построение нарративной структуры...")

    if not fragments:
        return {
            "story_type": "empty",
            "hook_fragment": 1,
            "chain": [],
        }

    # Начинаем с линейной структуры как базовой.
    result = _default_story(fragments, seed=seed)

    # Если стиль задан, уточняем тип истории (эвристика по длительности/числу фрагментов).
    if style_profile:
        n = len(fragments)
        total_duration = sum(float(f.get("duration", 0) or 0) for f in fragments)
        if n >= 3 and total_duration >= 60:
            result["story_type"] = "narrative"
        elif n >= 3:
            result["story_type"] = "montage"
        else:
            result["story_type"] = "vlog"

    # Применяем "золотые моменты" к выбору хука.
    result = await _apply_golden_moments(result, fragments, golden_moments)

    await ws_manager.broadcast(f"  ✅ Нарративная структура построена")
    return result


async def _apply_golden_moments(
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


def apply_story_structure(
    fragments: List[Dict],
    story: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Применяет нарративную структуру к списку фрагментов.

    Возвращает отсортированные фрагменты, исключённые (мусор) и карту
    темпа по фрагментам. Используется в pipeline.py.

    Returns:
        {
            "sorted_fragments": list[dict],
            "excluded": list,
            "scene_tempo": {int: str},
        }
    """
    chain = story.get("chain", [])
    hook_fragment = story.get("hook_fragment", 1)

    # Строим порядок из цепочки.
    ordered = []
    for item in chain:
        idx = item.get("fragment_index")
        if item.get("keep", True):
            ordered.append(idx)

    # Если цепочка пуста — используем все фрагменты по порядку.
    if not ordered:
        ordered = [f.get("index", i + 1) for i, f in enumerate(fragments)]

    # Гарантируем, что hook-фрагмент первый.
    if hook_fragment in ordered and ordered[0] != hook_fragment:
        ordered.remove(hook_fragment)
        ordered.insert(0, hook_fragment)

    index_to_frag = {f.get("index", i + 1): f for i, f in enumerate(fragments)}

    sorted_fragments = []
    scene_tempo: Dict[int, str] = {}
    excluded = []
    used_indices = set()

    for idx in ordered:
        frag = index_to_frag.get(idx)
        if frag is None:
            continue
        sorted_fragments.append(frag)
        used_indices.add(idx)
        # Темп берём из цепочки.
        tempo = "normal"
        for item in chain:
            if item.get("fragment_index") == idx:
                tempo = item.get("tempo", "normal")
                break
        scene_tempo[idx] = tempo

    # Фрагменты, не попавшие в цепочку/отсеянные, помечаем как исключённые.
    for i, f in enumerate(fragments):
        idx = f.get("index", i + 1)
        if idx not in used_indices:
            excluded.append(idx)

    return {
        "sorted_fragments": sorted_fragments,
        "excluded": excluded,
        "scene_tempo": scene_tempo,
    }