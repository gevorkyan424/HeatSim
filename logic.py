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

from typing import Dict, Tuple
import math


def _to_float(x) -> float:
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


def sum_both(cold: Dict[str, float], hot: Dict[str, float]) -> Tuple[float, float, float]:
    """
    Возвращает кортеж (sum_cold, sum_hot, sum_total)
    """
    s_cold = sum_flow(cold)
    s_hot = sum_flow(hot)
    return s_cold, s_hot, (s_cold + s_hot)


def named_sums(cold: Dict[str, float], hot: Dict[str, float]) -> Dict[str, float]:
    s_cold, s_hot, s_total = sum_both(cold, hot)
    return {"sum_cold": s_cold, "sum_hot": s_hot, "sum_total": s_total}


def calculate(cold: Dict[str, float], hot: Dict[str, float], cold_mix: list, hot_mix: list, q: float = 0.0) -> dict:
    """
    Улучшенная реализация расчёта:
    - Надёжно вычисляет Q, если он не задан и доступны температуры/расходы.
    - Вычисляет t_out_hot (t_out_plus) если Q задан и t_out_hot отсутствует.
    - Оценивает суммарный коэффициент теплоотдачи UA (в приложении помечается как 'k' [kW/K]) по методу LMTD: k = Q / LMTD.
    - Возвращает приближённую скорость производства энтропии σ ≈ Q*(1/T_cold_avg - 1/T_hot_avg).

    Возвращаемые ключи: возможно 'q', 't_out_plus', 'sigma', 'k'.
    Все температурные величины ожидаются в K, массы в кг/с, теплоёмкости в кДж/кг·K, Q в кВт.
    """

    def weighted_Cf(mix: list, t_ref: float) -> float:
        # mix: list of dicts with 'share', 'tb', 'cf', 'cp'
        s = 0.0
        for comp in mix or []:
            share = _to_float(comp.get('share', 0.0))
            tb = _to_float(comp.get('tb', 0.0))
            cf = _to_float(comp.get('cf', 0.0))
            cp = _to_float(comp.get('cp', 0.0))
            s += share * (cf if (t_ref is not None and t_ref < tb) else cp)
        return s

    out = {"sigma": 0.0, "k": 0.0}

    # safe inputs
    t_in_cold = _to_float(cold.get('t_in', 0.0))
    t_out_cold = _to_float(cold.get('t_out', 0.0))
    t_in_hot = _to_float(hot.get('t_in', 0.0))
    t_out_hot = _to_float(hot.get('t_out', 0.0))
    g_cold = _to_float(cold.get('m', 0.0))
    g_hot = _to_float(hot.get('m', 0.0))

    # capacity rates (kW/K) -- since Cf in kJ/kg·K and m in kg/s => m*Cf gives kJ/s/K == kW/K
    Cf_cold = weighted_Cf(cold_mix, t_in_cold)
    Cf_hot = weighted_Cf(hot_mix, t_in_hot)
    Cc = g_cold * Cf_cold
    Ch = g_hot * Cf_hot

    # 1) Compute Q when not provided
    if not q:
        q_candidates = []
        # validate mixes: require sum of shares approximately 1.0 for streams used in calc
        def mix_valid(mix: list) -> bool:
            try:
                if not mix: return False
                s = sum(_to_float(c.get('share', 0.0)) for c in mix)
                return abs(s - 1.0) <= 1e-3
            except Exception:
                return False

        cold_mix_ok = mix_valid(cold_mix)
        hot_mix_ok = mix_valid(hot_mix)

        # from cold stream if t_out provided and cold_mix is valid
        if cold_mix_ok and g_cold > 0.0 and Cf_cold > 0.0 and t_in_cold and t_out_cold:
            qc = Cc * (t_out_cold - t_in_cold)
            q_candidates.append(qc)
        # from hot stream if t_out provided and hot_mix is valid
        if hot_mix_ok and g_hot > 0.0 and Cf_hot > 0.0 and t_in_hot and t_out_hot:
            qh = Ch * (t_in_hot - t_out_hot)
            q_candidates.append(qh)

        if q_candidates:
            # if multiple estimates, take average
            q_est = sum(q_candidates) / len(q_candidates)
            out['q'] = round(q_est, 6)
            q = q_est

    # 2) If Q is provided (or computed) and t_out_hot missing -> compute it
    # require hot_mix to be valid for heat capacity estimate
    hot_mix_ok = (lambda mix: bool(mix) and abs(sum(_to_float(c.get('share',0.0)) for c in mix) - 1.0) <= 1e-3)(hot_mix)
    if q and (not t_out_hot) and g_hot > 0.0 and Cf_hot > 0.0 and t_in_hot and hot_mix_ok:
        try:
            t_out_plus = t_in_hot - (q / Ch)
            out['t_out_plus'] = round(t_out_plus, 6)
            t_out_hot = t_out_plus
        except Exception:
            pass

    # 3) Estimate UA (returned as 'k' in kW/K) using LMTD approximation when temperatures available
    try:
        # need terminal temperature differences: dT1 = Th_in - Tc_out, dT2 = Th_out - Tc_in
        if t_in_hot and t_out_hot and t_in_cold and t_out_cold and q:
            dT1 = t_in_hot - t_out_cold
            dT2 = t_out_hot - t_in_cold
            # both deltas must be positive for LMTD; take abs if sign reversed
            if dT1 == dT2:
                LMTD = dT1
            else:
                # avoid domain errors
                if dT1 <= 0 or dT2 <= 0:
                    LMTD = None
                else:
                    LMTD = (dT1 - dT2) / math.log(dT1 / dT2)

            if LMTD and abs(LMTD) > 1e-12:
                ua = q / LMTD
                out['k'] = float(ua)
    except Exception:
        out['k'] = 0.0

    # 4) Estimate entropy production σ ≈ Q*(1/Tc_avg - 1/Th_avg) (kW/K)
    try:
        if q:
            # choose average temperatures if both streams have in/out, else fall back to available
            Tc_avg = None
            Th_avg = None
            if t_in_cold and t_out_cold:
                Tc_avg = 0.5 * (t_in_cold + t_out_cold)
            elif t_in_cold:
                Tc_avg = t_in_cold
            if t_in_hot and t_out_hot:
                Th_avg = 0.5 * (t_in_hot + t_out_hot)
            elif t_in_hot:
                Th_avg = t_in_hot

            if Tc_avg and Th_avg and Tc_avg > 0 and Th_avg > 0:
                sigma = q * (1.0 / Tc_avg - 1.0 / Th_avg)
                out['sigma'] = float(sigma)
    except Exception:
        out['sigma'] = 0.0

    # normalize numeric outputs
    for k in ('q', 't_out_plus', 'sigma', 'k'):
        if k in out:
            try:
                out[k] = float(out[k])
            except Exception:
                pass

    return out
