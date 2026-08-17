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