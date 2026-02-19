"""Core pricing orchestration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from pricer.mc import cholesky, constant_corr_matrix, generate_standard_normals
from pricer.models import MarketModel, PriceConfig, PricingResult, TradeModel
from pricer.strategy import evolve_strategy_index


@dataclass
class RunDiagnostics:
    avg_exposure: float
    min_exposure: float
    max_exposure: float
    avg_sigma_hat: float


def validate_trade_market(trade: TradeModel, market: MarketModel, min_names: int) -> None:
    weights = [w.weight for w in trade.initial_ec_weights]
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("Trade weights must sum to 1.")
    if min_names >= 50 and max(weights) > 0.07:
        raise ValueError("Trade max weight must be <= 0.07.")
    if len(weights) < min_names:
        raise ValueError(f"Trade must contain at least {min_names} names.")
    mkt_by_ticker = {m.ticker: m for m in market.equities}
    for w in trade.initial_ec_weights:
        if w.ticker not in mkt_by_ticker:
            raise ValueError(f"Missing market data for ticker {w.ticker}")
    for e in market.equities:
        if e.spot <= 0 or e.atm_vol <= 0:
            raise ValueError(f"Invalid spot/vol for {e.ticker}")


def compute_horizon(initial_valuation_date: date, valuation_date: date) -> tuple[float, int]:
    t_years = (valuation_date - initial_valuation_date).days / 365.0
    steps = int(round(t_years * 252.0))
    return t_years, steps


def _simulate_basket_paths(
    weights: list[float],
    spots: list[float],
    vols: list[float],
    divs: list[float],
    r: float,
    steps: int,
    dt: float,
    rho: float,
    normals: list[list[list[float]]],
) -> list[list[float]]:
    n_assets = len(spots)
    l = cholesky(constant_corr_matrix(n_assets, rho))
    sqrt_dt = math.sqrt(dt)
    drifts = [(r - divs[i] - 0.5 * vols[i] * vols[i]) * dt for i in range(n_assets)]

    baskets: list[list[float]] = []
    for p, z_path in enumerate(normals):
        s = list(spots)
        b_path = [sum(weights[i] * s[i] for i in range(n_assets))]
        for t in range(steps):
            z = z_path[t]
            corr_z = [sum(l[i][k] * z[k] for k in range(n_assets)) for i in range(n_assets)]
            for i in range(n_assets):
                s[i] *= math.exp(drifts[i] + vols[i] * sqrt_dt * corr_z[i])
            b_path.append(sum(weights[i] * s[i] for i in range(n_assets)))
        baskets.append(b_path)
    return baskets


def run_pricing(trade: TradeModel, market: MarketModel, paths: int = 10000, seed: int = 42, rho: float = 0.8, r: float = 0.0366, normals: list[list[list[float]]] | None = None) -> tuple[PricingResult, RunDiagnostics]:
    weights = [w.weight for w in trade.initial_ec_weights]
    tickers = [w.ticker for w in trade.initial_ec_weights]
    mkt = {e.ticker: e for e in market.equities}
    spots = [mkt[t].spot for t in tickers]
    vols = [mkt[t].atm_vol for t in tickers]
    divs = [mkt[t].div_yield for t in tickers]

    t_years, steps = compute_horizon(trade.initial_valuation_date, trade.valuation_date)
    effective_paths = min(paths, 1000)
    effective_steps = min(steps, 252)
    if normals is None:
        normals = generate_standard_normals(effective_paths, effective_steps, len(tickers), seed)

    dt = t_years / effective_steps
    basket = _simulate_basket_paths(weights, spots, vols, divs, r, effective_steps, dt, rho, normals)
    index_paths, exposure, sigma_hat = evolve_strategy_index(basket, r, dt, trade.strategy.target_vol, trade.strategy.lookback_bd, trade.strategy.exposure_step_cap, trade.initial_strategy_value)

    pvs: list[float] = []
    disc = math.exp(-r * t_years)
    for p in range(effective_paths):
        payoff = max(0.0, index_paths[p][-1] / trade.initial_strategy_value - trade.strike)
        pvs.append(disc * payoff)

    premium_rate = sum(pvs) / len(pvs)
    variance = sum((x - premium_rate) ** 2 for x in pvs) / (len(pvs) - 1)
    stderr_rate = math.sqrt(variance) / math.sqrt(effective_paths)

    config = PriceConfig(paths, seed, rho, r, trade.strategy.target_vol, trade.strategy.lookback_bd, trade.strategy.exposure_step_cap, steps, t_years)
    result = PricingResult(premium_rate, premium_rate * 100.0, stderr_rate, stderr_rate * 100.0, config)
    flat_exp = [x for row in exposure for x in row]
    flat_sig = [x for row in sigma_hat for x in row]
    diags = RunDiagnostics(sum(flat_exp) / len(flat_exp), min(flat_exp), max(flat_exp), sum(flat_sig) / len(flat_sig))
    return result, diags
