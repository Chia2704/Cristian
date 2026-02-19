"""Greeks computation via bump-and-reprice with common random numbers."""

from __future__ import annotations

from pricer.mc import generate_standard_normals
from pricer.models import MarketModel, TradeModel
from pricer.pricer import compute_horizon, run_pricing

DELTA_BUMP_REL = 0.01
VEGA_BUMP_ABS = 0.01
RHO_BUMP_ABS = 0.0001


def compute_greeks(
    trade: TradeModel,
    market: MarketModel,
    paths: int,
    seed: int,
    rho: float,
    r: float,
    use_crn: bool = True,
) -> list[dict[str, float | str]]:
    t_years, steps = compute_horizon(trade.initial_valuation_date, trade.valuation_date)
    _ = t_years
    normals = generate_standard_normals(paths, steps, len(trade.initial_ec_weights), seed) if use_crn else None
    base, _ = run_pricing(trade, market, paths, seed, rho, r, normals=normals)

    rows: list[dict[str, float | str]] = []
    for idx, eq in enumerate(market.equities):
        bumped_eq = eq.model_copy(update={"spot": eq.spot * (1.0 + DELTA_BUMP_REL)})
        bumped_market = market.model_copy(update={"equities": [bumped_eq if i == idx else e for i, e in enumerate(market.equities)]})
        bumped, _ = run_pricing(trade, bumped_market, paths, seed, rho, r, normals=normals)
        rows.append({"name": f"DELTA_{eq.ticker}", "value": (bumped.premium_rate - base.premium_rate) / DELTA_BUMP_REL})

    vol_market = market.model_copy(update={"equities": [e.model_copy(update={"atm_vol": e.atm_vol + VEGA_BUMP_ABS}) for e in market.equities]})
    vega, _ = run_pricing(trade, vol_market, paths, seed, rho, r, normals=normals)
    rows.append({"name": "VEGA", "value": (vega.premium_rate - base.premium_rate) / VEGA_BUMP_ABS})

    rho_r, _ = run_pricing(trade, market, paths, seed, rho, r + RHO_BUMP_ABS, normals=normals)
    rows.append({"name": "RHO", "value": (rho_r.premium_rate - base.premium_rate) / RHO_BUMP_ABS})
    return rows
