"""analysis_logic.py

Логика для окна анализа: перебор вариаций долей компонентов и
вычисление зависимости Q и σ (sigma).

Использует существующую функцию logic.calculate.
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple, cast
import logic


def vary_component_shares(
    cold_mix: List[Dict[str, Any]],
    hot_mix: List[Dict[str, Any]],
    step: float = 0.1,
    limit: int = 200,
) -> List[Tuple[float, float]]:
    """Генерирует набор (Q, sigma) при варьировании одной доли в каждой смеси.

    Алгоритм упрощён: выбирается первый компонент в каждой смеси и его доля
    варьируется в пределах [0,1] c шагом `step`, оставшаяся доля пропорционально
    распределяется между остальными компонентами.
    """
    points: List[Tuple[float, float]] = []
    if not cold_mix or not hot_mix:
        return points
    base_cold = list(cold_mix)
    base_hot = list(hot_mix)
    cold_rest = base_cold[1:]
    hot_rest = base_hot[1:]
    for val in frange(0.0, 1.0, step):
        if len(points) >= limit:
            break
        # normalize cold
        new_cold = []
        if cold_rest:
            rest_share_cold = (1.0 - val) / max(1, len(cold_rest))
            new_cold.append({**base_cold[0], "share": val})
            for c in cold_rest:
                new_cold.append({**c, "share": rest_share_cold})
        else:
            new_cold.append({**base_cold[0], "share": 1.0})
        # normalize hot
        new_hot = []
        if hot_rest:
            rest_share_hot = (1.0 - val) / max(1, len(hot_rest))
            new_hot.append({**base_hot[0], "share": val})
            for h in hot_rest:
                new_hot.append({**h, "share": rest_share_hot})
        else:
            new_hot.append({**base_hot[0], "share": 1.0})
        ans = logic.calculate(
            cold={"t_in": 0.0, "t_out": 0.0, "m": 0.0, "p": 0.0},
            hot={"t_in": 0.0, "t_out": 0.0, "m": 0.0, "p": 0.0},
            cold_mix=cast(List[Dict[str, Any]], new_cold),
            hot_mix=cast(List[Dict[str, Any]], new_hot),
            q=0.0,
            schema="Schema1",
        )
        q_val = float(ans.get("q", 0.0))  # type: ignore[arg-type]
        sigma_val = float(ans.get("sigma", 0.0))  # type: ignore[arg-type]
        points.append((q_val, sigma_val))
    return points


def frange(start: float, stop: float, step: float):
    x = start
    while x <= stop + 1e-12:
        yield round(x, 10)
        x += step


__all__ = ["vary_component_shares"]
