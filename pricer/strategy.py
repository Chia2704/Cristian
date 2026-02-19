"""Vol-target strategy index evolution logic."""

from __future__ import annotations

import math


def _sigma_from_stats(count: int, s: float, ss: float, target_vol: float) -> float:
    if count < 2:
        return target_vol
    mean = s / count
    var = (ss - count * mean * mean) / (count - 1)
    return math.sqrt(max(var, 0.0)) * math.sqrt(252.0)


def evolve_strategy_index(
    basket_levels: list[list[float]],
    r: float,
    dt: float,
    target_vol: float,
    lookback_bd: int,
    step_cap: float,
    i0: float = 100.0,
) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    paths = len(basket_levels)
    steps = len(basket_levels[0]) - 1
    index = [[0.0] * (steps + 1) for _ in range(paths)]
    exposure = [[0.0] * steps for _ in range(paths)]
    sigma_hat_all = [[0.0] * steps for _ in range(paths)]

    for p in range(paths):
        index[p][0] = i0
        a_prev = 1.0
        window: list[float] = []
        ws = 0.0
        wss = 0.0
        for t in range(steps):
            b_t = basket_levels[p][t]
            b_tp1 = basket_levels[p][t + 1]
            lr = math.log(b_tp1 / b_t)
            window.append(lr)
            ws += lr
            wss += lr * lr
            if len(window) > lookback_bd:
                old = window.pop(0)
                ws -= old
                wss -= old * old

            sig = _sigma_from_stats(len(window), ws, wss, target_vol)
            sigma_hat_all[p][t] = sig
            a_star = min(1.0, target_vol / max(sig, 1e-12))
            a_t = min(a_prev + step_cap, max(a_prev - step_cap, a_star))
            a_t = min(1.0, max(0.0, a_t))
            exposure[p][t] = a_t

            r_basket = b_tp1 / b_t - 1.0
            r_cash = r * dt
            index[p][t + 1] = index[p][t] * (1.0 + a_t * r_basket + (1.0 - a_t) * r_cash)
            a_prev = a_t
    return index, exposure, sigma_hat_all
