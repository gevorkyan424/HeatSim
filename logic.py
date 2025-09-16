# logic.py
"""
Physics and formulas used in calculations.

Units and variable conventions used in code:
- Temperatures: Kelvin (K)
- Mass flow: kg/s
- Specific heat (c_f, c_p): kJ/(kg·K)
- Power Q: kW

Key formulas implemented below:

1) Heat balance for each stream
    Q = C_h * (T_h_in - T_h_out)      # hot stream
    Q = C_c * (T_c_out - T_c_in)      # cold stream
    where C = m * c_mix (kW/K because c in kJ/kg·K and m in kg/s)

2) Solve for T_h_out when Q known:
    T_h_out = T_h_in - Q / C_h

3) Effective specific heat of mixture (simple weighted average)
    c_mix(T_ref) = sum_i x_i * c_i(T_ref)
    where c_i(T_ref) = c_f,i if T_ref < T_b,i else c_p,i

4) LMTD-based estimate for UA (returned as 'k' in kW/K):
    dT1 = T_h_in - T_c_out
    dT2 = T_h_out - T_c_in
    LMTD = (dT1 - dT2) / ln(dT1/dT2)  (if dT1 != dT2)
    UA ≈ Q / LMTD

5) Approximate entropy production (sigma):
    sigma ≈ Q * (1/T_c_avg - 1/T_h_avg)

This module exposes `calculate(cold, hot, cold_mix, hot_mix, q=0.0)` which returns
a dict possibly containing keys: 'q', 't_out_plus', 'sigma', 'k'.
"""

from typing import Dict, Tuple, Any, List, Union
import math


def _to_float(x: Any) -> float:
    """Безопасно приводит значение к float."""
    try:
        return float(x)
    except Exception:
        return 0.0


def sum_flow(flow: Dict[str, float]) -> float:
    """
    Сумма ВСЕХ числовых значений словаря одного потока.
    Пример: t_in + t_out + m + p.
    """
    return sum(_to_float(v) for v in flow.values())


def sum_both(
    cold: Dict[str, float], hot: Dict[str, float]
) -> Tuple[float, float, float]:
    """
    Возвращает кортеж (sum_cold, sum_hot, sum_total)
    """
    s_cold = sum_flow(cold)
    s_hot = sum_flow(hot)
    return s_cold, s_hot, (s_cold + s_hot)


def named_sums(cold: Dict[str, float], hot: Dict[str, float]) -> Dict[str, float]:
    s_cold, s_hot, s_total = sum_both(cold, hot)
    return {"sum_cold": s_cold, "sum_hot": s_hot, "sum_total": s_total}


def calculate(
    cold: Dict[str, float],
    hot: Dict[str, float],
    cold_mix: List[Dict[str, Any]],
    hot_mix: List[Dict[str, Any]],
    q: float = 0.0,
    schema: str = "Schema1",
) -> Dict[str, Union[float, str]]:
    """
    Улучшенная реализация расчёта:
    - Надёжно вычисляет Q, если он не задан и доступны температуры/расходы.
    - Вычисляет t_out_hot (t_out_plus) если Q задан и t_out_hot отсутствует.
    - Оценивает суммарный коэффициент теплоотдачи UA (в приложении помечается как 'k' [kW/K]) по методу LMTD: k = Q / LMTD.
    - Возвращает приближённую скорость производства энтропии σ ≈ Q*(1/T_cold_avg - 1/T_hot_avg).

    Возвращаемые ключи: возможно 'q', 't_out_plus', 'sigma', 'k'.
    Все температурные величины ожидаются в K, массы в кг/с, теплоёмкости в кДж/кг·K, Q в кВт.
    """

    def weighted_Cf(mix: List[Dict[str, Any]], t_ref: float) -> float:
        # mix: list of dicts with 'share', 'tb', 'cf', 'cp'
        s = 0.0
        for comp in mix or []:
            share = _to_float(comp.get("share", 0.0))
            tb = _to_float(comp.get("tb", 0.0))
            cf = _to_float(comp.get("cf", 0.0))
            cp = _to_float(comp.get("cp", 0.0))
            s += share * (cf if (t_ref < tb) else cp)
        return s

    out = {"sigma": 0.0, "k": 0.0, "k_source": "", "contact_type": ""}

    # safe inputs
    t_in_cold = _to_float(cold.get("t_in", 0.0))
    t_out_cold = _to_float(cold.get("t_out", 0.0))
    t_in_hot = _to_float(hot.get("t_in", 0.0))
    t_out_hot = _to_float(hot.get("t_out", 0.0))
    g_cold = _to_float(cold.get("m", 0.0))
    g_hot = _to_float(hot.get("m", 0.0))

    # capacity rates (kW/K) -- since Cf in kJ/kg·K and m in kg/s => m*Cf gives kJ/s/K == kW/K
    Cf_cold = weighted_Cf(cold_mix, t_in_cold)
    Cf_hot = weighted_Cf(hot_mix, t_in_hot)
    # (Capacity rates retained as Cf_* only; previous variables Cc/Ch removed to avoid unused warnings)

    # 1) Новая логика вычисления Q (адаптация C# pamQ):
    # Если Q не задан (0) и известны все температуры (включая t_out_hot) + расход холодного потока ->
    #   считаем теплоёмкость холодного потока и Q = (T_in_hot - T_out_hot) * W_cold
    if (not q) and all([t_in_cold, t_out_cold, t_in_hot, t_out_hot, g_cold > 0.0]):
        if Cf_cold > 0.0:
            W_cold = g_cold * Cf_cold  # kW/K
            q_est = (t_in_hot - t_out_hot) * W_cold
            out["q"] = round(q_est, 6)
            q = q_est

    # 2) Новая логика вычисления t_out_hot (адаптация C# pamTout):
    # Если Q уже задан (или вычислен) и отсутствует t_out_hot, но есть вход горячего и расход горячего ->
    #   вычисляем теплоёмкость горячего потока и t_out_hot = T_in_hot - Q / W_hot
    if q and (not t_out_hot) and all([t_in_hot, g_hot > 0.0]) and Cf_hot > 0.0:
        try:
            W_hot = g_hot * Cf_hot
            if W_hot > 0:
                t_out_plus = t_in_hot - (q / W_hot)
                out["t_out_plus"] = round(t_out_plus, 6)
                t_out_hot = t_out_plus
        except Exception:
            pass

    # 3) Расчёт Sigma и K по единой логике (одно- или многокомпонентный случай)
    try:
        # Подготовим облегчённый FlowState (не экспортируем наружу, только локально)
        # Переписываем mixes в структуру Component, но используем только требуемые поля.
        def to_components(mix: List[Dict[str, Any]]) -> List[Component]:
            comps: List[Component] = []
            for item in mix or []:
                try:
                    share = _to_float(item.get("share", 0.0))  # type: ignore[arg-type]
                    tb = _to_float(item.get("tb", 0.0))  # type: ignore[arg-type]
                    cf = _to_float(item.get("cf", 0.0))  # type: ignore[arg-type]
                    cp = _to_float(item.get("cp", 0.0))  # type: ignore[arg-type]
                    rf = _to_float(item.get("rf", 0.0))  # type: ignore[arg-type]
                    comps.append(Component(Share=share, T_b=tb, C_f=cf, C_p=cp, r_f=rf))
                except Exception:
                    pass
            return comps

        cold_components = to_components(cold_mix)
        hot_components = to_components(hot_mix)

        # FlowState
        fs = FlowState(
            T_in_cold=t_in_cold,
            T_out_cold=t_out_cold,
            T_in_hot=t_in_hot,
            T_out_hot=t_out_hot,
            g_cold=g_cold,
            g_hot=g_hot,
            Q=q or 0.0,
            schema=schema,
        )

        # Заполняем W_cold/W_hot, A/B и вычисляем Sigma/K через full()
        full(fs, cold_components, hot_components)

        # Если при выполнении схемы в однофазном случае Q или K изменились (схемы могут модифицировать)
        # синхронизируем их в out (не перезаписываем ранее вычисленный q если он отсутствовал в схемном результате)
        if fs.Q and "q" not in out:
            out["q"] = round(fs.Q, 6)
        # Если t_out_hot был не задан и схема/ full() ничего не посчитала, оставляем как есть. В противном случае
        # (однофазный путь не вычисляет t_out_hot заново — уже сделано выше в шаге 2 если требовалось).

        if fs.Sigma:
            out["sigma"] = float(fs.Sigma)
        if fs.K:
            out["k"] = float(fs.K)
            out["k_source"] = "schema/contact"
        # Если σ вычислена, но K не найден — попробуем простую эвристику по средней температурной разнице
        if (not fs.K) and fs.Sigma and (fs.Q or q):
            try:
                # средние температуры на горячей и холодной сторонах
                Th_mean = None
                Tc_mean = None
                if fs.T_in_hot and fs.T_out_hot:
                    Th_mean = 0.5 * (fs.T_in_hot + fs.T_out_hot)
                if fs.T_in_cold and fs.T_out_cold:
                    Tc_mean = 0.5 * (fs.T_in_cold + fs.T_out_cold)
                if Th_mean and Tc_mean:
                    delta_mean = Th_mean - Tc_mean
                    if delta_mean > 0:
                        q_used = fs.Q or q
                        k_est = q_used / delta_mean
                        out["k"] = float(round(k_est, 6))
                        out["k_source"] = "mean_delta"
            except Exception:
                pass
        # contact type (multicomponent) если определён
        if getattr(fs, "contact_type", None):
            out["contact_type"] = str(fs.contact_type)
        # Fallback: если K не посчитан контактными/схемными формулами, попробуем LMTD при наличии данных
        if (
            (not fs.K)
            and (q or fs.Q)
            and t_in_hot
            and t_out_hot
            and t_in_cold
            and t_out_cold
        ):
            try:
                # Use heat duty from fs if available
                q_used = fs.Q or q
                dT1 = t_in_hot - t_out_cold
                dT2 = t_out_hot - t_in_cold
                if dT1 > 0 and dT2 > 0 and dT1 != dT2:
                    lmtd = (dT1 - dT2) / math.log(dT1 / dT2)
                elif dT1 == dT2 and dT1 > 0:
                    lmtd = dT1
                else:
                    lmtd = 0.0
                if lmtd > 0:
                    k_lmtd = q_used / lmtd
                    out["k"] = float(round(k_lmtd, 6))
                    out["k_source"] = "lmtd"
            except Exception:
                pass
    except Exception:
        pass

    # normalize numeric outputs
    for k in ("q", "t_out_plus", "sigma", "k"):
        if k in out:
            try:
                out[k] = float(out[k])
            except Exception:
                pass

    return out


# ---------------------------------------------------------------------------
# Translation layer from provided C# formulas.
# Keeps original calculate() intact; provides an alternative API oriented
# around a FlowState class similar to the F1 structure in the C# snippet.
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Component:
    Share: float
    T_b: float  # boiling / phase-change threshold temperature
    C_f: float  # specific heat below T_b (kJ/kg*K)
    C_p: float  # specific heat above T_b (kJ/kg*K)
    r_f: float = 0.0  # latent heat term (kJ/kg) if phase change


@dataclass
class FlowState:
    # Temperatures (K)
    T_in_cold: float = 0.0
    T_out_cold: float = 0.0
    T_in_hot: float = 0.0
    T_out_hot: float = 0.0

    # Mass flow rates (kg/s)
    g_cold: float = 0.0
    g_hot: float = 0.0

    # Heat transfer related
    Q: float = 0.0  # kW
    K: float = 0.0  # (kW/K) aggregated coefficient (UA)
    Sigma: float = 0.0  # entropy production approximation

    # Derived capacity rates (kW/K)
    W_cold: float = 0.0
    W_hot: float = 0.0
    W: float = 0.0  # optional common capacity when equal

    # Auxiliary variables A, B per C# code
    A: float = 0.0
    B: float = 0.0

    # Counters for components
    countCold: int = 0
    countHot: int = 0

    # Selected schema label (Schema1..Schema5)
    schema: str = "Schema1"

    # Cached contact type for multi-component operations
    contact_type: Optional[str] = None


def _capacity_from_components(components: List[Component], T_ref: float) -> float:
    return sum(c.Share * (c.C_f if T_ref < c.T_b else c.C_p) for c in components)


def pamQ(
    state: FlowState, cold_components: List[Component], hot_components: List[Component]
):
    if cold_components and hot_components:
        state.countCold = len(cold_components)
        state.countHot = len(hot_components)
    if (
        state.T_in_cold
        and state.T_out_cold
        and state.T_in_hot
        and state.T_out_hot
        and state.g_cold
        and state.Q == 0.0
    ):
        Cf_cold = _capacity_from_components(cold_components, state.T_in_cold)
        state.W_cold = state.g_cold * Cf_cold
    # Q from hot side definition in C# snippet: (T_in_hot - T_out_hot) * W_cold
    if state.W_cold:
        state.Q = round((state.T_in_hot - state.T_out_hot) * state.W_cold, 5)


def pamTout(
    state: FlowState, cold_components: List[Component], hot_components: List[Component]
):
    if cold_components and hot_components:
        state.countCold = len(cold_components)
        state.countHot = len(hot_components)
    if (
        state.T_in_cold
        and state.T_out_cold
        and state.T_in_hot
        and state.Q
        and state.g_hot
        and state.T_out_hot == 0.0
    ):
        Cf_hot = _capacity_from_components(hot_components, state.T_in_hot)
        state.W_hot = state.g_hot * Cf_hot
    if state.W_hot:
        state.T_out_hot = round(state.T_in_hot - (state.Q / state.W_hot), 5)


def _get_contact_type(
    state: FlowState, cold_components: List[Component], hot_components: List[Component]
) -> str:
    isColdBoiling = any(
        state.T_in_cold < c.T_b and state.T_out_cold > c.T_b for c in cold_components
    )
    isHotCondensing = any(
        state.T_in_hot > c.T_b and state.T_out_hot < c.T_b for c in hot_components
    )
    if not isHotCondensing and not isColdBoiling:
        return "dd"
    elif not isHotCondensing and isColdBoiling:
        return "db"
    elif isHotCondensing and isColdBoiling:
        return "cb"
    else:
        return "cd"


def _sigma_dd(state: FlowState):
    # Single-phase both sides (variant uses Q and derived outlet temps)
    if state.W_hot and state.W_cold and state.T_in_hot and state.T_in_cold and state.Q:
        Th_out = state.T_in_hot - state.Q / state.W_hot
        Tc_out = state.T_in_cold + state.Q / state.W_cold
        state.Sigma = round(
            state.W_hot * math.log(Th_out / state.T_in_hot)
            + state.W_cold * math.log(Tc_out / state.T_in_cold),
            5,
        )


def _k_dd(state: FlowState):
    # Direct transcription from provided C# (with caution – original formula looked suspicious)
    if (
        state.A
        and state.W_hot
        and state.W_cold
        and state.T_in_hot
        and state.T_in_cold
        and state.Q
    ):
        try:
            Th_out = state.T_in_hot - state.Q / state.W_hot
            Tc_out = state.T_in_cold + state.Q / state.W_cold
            numerator = Th_out - Tc_out
            denominator = state.T_in_hot - state.T_in_cold
            if denominator != 0 and state.A != 0 and numerator > 0:
                state.K = round((1.0 / state.A) * math.log(numerator / denominator), 5)
        except Exception:
            pass


def _sigma_db(state: FlowState, cold_components: List[Component]):
    acc = 0.0
    for c in cold_components:
        if state.T_in_cold < c.T_b < state.T_out_cold:
            if c.T_b:
                acc += (state.g_cold * c.Share * c.r_f) / c.T_b
    # plus hot side sensible
    if state.W_hot and state.T_in_hot:
        Th_out = (
            state.T_in_hot - state.Q / state.W_hot
            if state.Q and state.W_hot
            else state.T_out_hot
        )
        if Th_out and Th_out > 0:
            try:
                acc += state.W_hot * math.log(Th_out / state.T_in_hot)
            except Exception:
                pass
    state.Sigma = round(acc, 5)


def _k_db(state: FlowState, cold_components: List[Component]):
    cand = [
        c.T_b for c in cold_components if state.T_in_cold < c.T_b < state.T_out_cold
    ]
    if cand and state.T_in_hot:
        Tb_mean = sum(cand) / len(cand)
        if (state.T_in_hot - Tb_mean) != 0:
            state.K = round(state.Q / (state.T_in_hot - Tb_mean), 5)


def _sigma_cb(
    state: FlowState, cold_components: List[Component], hot_components: List[Component]
):
    acc = 0.0
    for c in cold_components:
        if state.T_in_cold < c.T_b < state.T_out_cold and c.T_b:
            acc += (state.g_cold * c.Share * c.r_f) / c.T_b
    for c in hot_components:
        if state.T_in_hot > c.T_b > state.T_out_hot and c.T_b:
            acc -= (state.g_hot * c.Share * c.r_f) / c.T_b
    state.Sigma = round(acc, 5)


def _k_cb(
    state: FlowState, cold_components: List[Component], hot_components: List[Component]
):
    cold_tb = [
        c.T_b for c in cold_components if state.T_in_cold < c.T_b < state.T_out_cold
    ]
    hot_tb = [c.T_b for c in hot_components if state.T_in_hot > c.T_b > state.T_out_hot]
    if cold_tb and hot_tb:
        Tb_cold = sum(cold_tb) / len(cold_tb)
        Tb_hot = sum(hot_tb) / len(hot_tb)
        if (Tb_hot - Tb_cold) != 0:
            state.K = round(state.Q / (Tb_hot - Tb_cold), 5)


def _sigma_cd(state: FlowState, hot_components: List[Component]):
    acc = 0.0
    for c in hot_components:
        if state.T_in_hot > c.T_b > state.T_out_hot and c.T_b:
            acc -= (state.g_hot * c.Share * c.r_f) / c.T_b
    # cold side sensible
    if state.W_cold and state.T_in_cold:
        Tc_out = (
            state.T_in_cold + state.Q / state.W_cold
            if state.Q and state.W_cold
            else state.T_out_cold
        )
        if Tc_out and Tc_out > 0:
            try:
                acc += state.W_cold * math.log(Tc_out / state.T_in_cold)
            except Exception:
                pass
    state.Sigma = round(acc, 5)


def _k_cd(state: FlowState, hot_components: List[Component]):
    cand = [c.T_b for c in hot_components if state.T_in_hot > c.T_b > state.T_out_hot]
    if cand:
        Tb_mean = sum(cand) / len(cand)
        if (Tb_mean - state.T_in_cold) != 0:
            state.K = round(state.Q / (Tb_mean - state.T_in_cold), 5)


def _schema1(state: FlowState):
    # Mixing-mixing: derive missing variable only
    delta = state.T_out_hot - state.T_out_cold
    if delta != 0:
        if state.Q > 0 and state.K == 0:
            state.K = round(state.Q / delta, 5)
        elif state.K > 0 and state.Q == 0:
            state.Q = round(state.K * delta, 5)


def _schema2(state: FlowState):
    # Parallel flow (displacement-displacement): solve one direction
    if state.B:
        try:
            if state.Q > 0 and state.K == 0:
                denom = state.T_in_hot - state.T_in_cold - (state.B * state.Q)
                if denom and (state.T_in_hot - state.T_in_cold) / denom > 0:
                    state.K = round(
                        (1 / state.B)
                        * math.log((state.T_in_hot - state.T_in_cold) / denom),
                        5,
                    )
            elif state.K > 0 and state.Q == 0:
                term = 1 - math.exp(-state.K * state.B)
                state.Q = round(
                    (1 / state.B) * (state.T_in_hot - state.T_in_cold) * term, 5
                )
        except Exception:
            pass


def _schema3(state: FlowState):
    # Cold mixing - hot displacement
    if state.W_hot:
        try:
            if state.Q > 0 and state.K == 0:
                denom = state.T_in_hot - state.T_out_hot - (state.Q / state.W_hot)
                if denom and (state.T_in_hot - state.T_out_cold) / denom > 0:
                    state.K = round(
                        state.W_hot
                        * math.log((state.T_in_hot - state.T_out_cold) / denom),
                        5,
                    )
            elif state.K > 0 and state.Q == 0:
                term = 1 - math.exp(-(state.K / state.W_hot))
                state.Q = round(
                    state.W_cold * (state.T_in_hot - state.T_out_cold) * term, 5
                )
        except Exception:
            pass


def _schema4(state: FlowState):
    # Hot mixing - cold displacement
    if state.W_cold:
        try:
            if state.Q > 0 and state.K == 0:
                denom = state.T_out_hot - state.T_in_cold - (state.Q / state.W_cold)
                if denom and (state.T_out_hot - state.T_in_cold) / denom > 0:
                    state.K = round(
                        state.W_cold
                        * math.log((state.T_out_hot - state.T_in_cold) / denom),
                        5,
                    )
            elif state.K > 0 and state.Q == 0:
                term = 1 - math.exp(-(state.K / state.W_cold))
                state.Q = round(
                    state.W_cold * (state.T_out_hot - state.T_in_cold) * term, 5
                )
        except Exception:
            pass


def _schema5(state: FlowState):
    # Counterflow (displacement-displacement)
    if state.A:
        try:
            if state.Q > 0 and state.K == 0:
                denom = state.T_out_hot - state.T_in_cold
                if denom and (denom + (state.A * state.Q)) / denom > 0:
                    state.K = round(
                        (1 / state.A) * math.log((denom + (state.A * state.Q)) / denom),
                        5,
                    )
                if state.W_cold == state.W_hot and state.W_cold and state.K == 0:
                    state.W = state.W_cold
                    denom2 = state.T_in_hot - state.T_in_cold - (state.Q / state.W)
                    if denom2:
                        state.K = round(state.Q / denom2, 5)
            elif state.K > 0 and state.Q == 0:
                state.Q = round(
                    (1 / state.A)
                    * (state.T_out_hot - state.T_in_cold)
                    * (math.exp(state.K * state.A) - 1),
                    5,
                )
                if state.W_cold == state.W_hot and state.W_cold:
                    state.W = state.W_cold
                    state.Q = round(
                        (state.W * (state.T_in_hot - state.T_in_cold) * state.K)
                        / (state.W + state.K),
                        5,
                    )
        except Exception:
            pass


def full(
    state: FlowState, cold_components: List[Component], hot_components: List[Component]
):
    # Compute capacities if not yet set
    if cold_components:
        Cf_cold = _capacity_from_components(cold_components, state.T_in_cold)
        state.W_cold = state.g_cold * Cf_cold
    if hot_components:
        Cf_hot = _capacity_from_components(hot_components, state.T_in_hot)
        state.W_hot = state.g_hot * Cf_hot

    if state.W_cold and state.W_hot:
        state.A = (state.W_cold - state.W_hot) / (state.W_hot * state.W_cold)
        state.B = (state.W_cold + state.W_hot) / (state.W_hot * state.W_cold)

    is_multicomponent = len(cold_components) > 1 or len(hot_components) > 1

    if not is_multicomponent:
        # Schema dispatch
        schema_map = {
            "Schema1": _schema1,
            "Schema2": _schema2,
            "Schema3": _schema3,
            "Schema4": _schema4,
            "Schema5": _schema5,
        }
        fn = schema_map.get(state.schema, _schema1)
        fn(state)
        # After schema-specific adjustments, recompute single-component Sigma
        if all(
            [
                state.W_hot,
                state.W_cold,
                state.T_out_hot,
                state.T_in_hot,
                state.T_out_cold,
                state.T_in_cold,
            ]
        ):
            try:
                state.Sigma = round(
                    (state.W_hot * math.log(state.T_out_hot / state.T_in_hot))
                    + (state.W_cold * math.log(state.T_out_cold / state.T_in_cold)),
                    5,
                )
            except Exception:
                pass
    else:
        # Multi-component path
        state.contact_type = _get_contact_type(state, cold_components, hot_components)
        if state.contact_type == "dd":
            _sigma_dd(state)
            _k_dd(state)
        elif state.contact_type == "db":
            _sigma_db(state, cold_components)
            _k_db(state, cold_components)
        elif state.contact_type == "cb":
            _sigma_cb(state, cold_components, hot_components)
            _k_cb(state, cold_components, hot_components)
        elif state.contact_type == "cd":
            _sigma_cd(state, hot_components)
            _k_cd(state, hot_components)

    return state


__all__ = ["calculate", "FlowState", "Component", "pamQ", "pamTout", "full"]
