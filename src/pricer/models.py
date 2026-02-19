"""Lightweight data models used by the pricer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from typing import Any


def _parse_date(v: Any) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


@dataclass
class WeightItem:
    ticker: str
    weight: float
    name: str | None = None


@dataclass
class StrategyParams:
    target_vol: float = 0.10
    lookback_bd: int = 40
    exposure_step_cap: float = 0.20


@dataclass
class TradeModel:
    trade_date: date
    initial_valuation_date: date
    valuation_date: date
    strike: float
    initial_strategy_value: float
    strategy: StrategyParams
    V_millions_range: dict[str, float]
    initial_ec_weights: list[WeightItem]

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "TradeModel":
        return cls(
            trade_date=_parse_date(data["trade_date"]),
            initial_valuation_date=_parse_date(data["initial_valuation_date"]),
            valuation_date=_parse_date(data["valuation_date"]),
            strike=float(data["strike"]),
            initial_strategy_value=float(data["initial_strategy_value"]),
            strategy=StrategyParams(**data["strategy"]),
            V_millions_range={k: float(v) for k, v in data["V_millions_range"].items()},
            initial_ec_weights=[WeightItem(**w) for w in data["initial_ec_weights"]],
        )

    def model_dump(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trade_date"] = self.trade_date.isoformat()
        payload["initial_valuation_date"] = self.initial_valuation_date.isoformat()
        payload["valuation_date"] = self.valuation_date.isoformat()
        return payload


@dataclass
class EquityMarketItem:
    ticker: str
    spot: float
    atm_vol: float
    div_yield: float

    def model_copy(self, update: dict[str, Any]) -> "EquityMarketItem":
        return replace(self, **update)


@dataclass
class CorrelationModel:
    type: str = "constant_cross_asset"
    rho: float = 0.8


@dataclass
class SOFRCurve:
    type: str = "flat_zero_rate"
    zero_rate: float = 0.0366
    day_count: str = "ACT/365F"
    compounding: str = "continuous"


@dataclass
class RatesModel:
    sofr_ois_curve: SOFRCurve


@dataclass
class MarketModel:
    equities: list[EquityMarketItem]
    correlation: CorrelationModel
    rates: RatesModel

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "MarketModel":
        return cls(
            equities=[EquityMarketItem(**e) for e in data["equities"]],
            correlation=CorrelationModel(**data.get("correlation", {})),
            rates=RatesModel(sofr_ois_curve=SOFRCurve(**data["rates"]["sofr_ois_curve"])),
        )

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

    def model_copy(self, update: dict[str, Any]) -> "MarketModel":
        return replace(self, **update)


@dataclass
class PriceConfig:
    paths: int
    seed: int
    rho: float
    r: float
    target_vol: float
    lookback_bd: int
    step_cap: float
    steps: int
    T_years: float


@dataclass
class PricingResult:
    premium_rate: float
    premium_per_100: float
    stderr_rate: float
    stderr_per_100: float
    config: PriceConfig

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)
