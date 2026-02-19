"""CLI commands for the MVP Monte Carlo pricer."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from pricer.greeks import compute_greeks
from pricer.io import read_basket_excel, read_json, read_market_excel, write_json
from pricer.models import CorrelationModel, EquityMarketItem, MarketModel, RatesModel, SOFRCurve, StrategyParams, TradeModel, WeightItem
from pricer.pricer import run_pricing, validate_trade_market
from pricer.report import write_manifest, write_pricing_outputs

DEFAULT_PATHS = 10000
DEFAULT_SEED = 42
DEFAULT_RHO = 0.8
DEFAULT_SOFR = 0.0366
DEFAULT_TARGET_VOL = 0.10
DEFAULT_LOOKBACK = 40
DEFAULT_STEP_CAP = 0.20


def _parse_date(value: str | None, default_value: date) -> date:
    return default_value if value is None else datetime.strptime(value, "%Y-%m-%d").date()


def _normalize_rate_col(x: float) -> float:
    return x / 100.0 if x > 2 else x


def build_trade_cmd(args: argparse.Namespace) -> None:
    rows = read_basket_excel(args.basket_xlsx)
    weights = [float(r["weight"]) for r in rows]
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("weights must sum to 1")
    if args.min_names >= 50 and max(weights) > 0.07:
        raise ValueError("max weight must be <= 0.07")
    if len(rows) < args.min_names:
        raise ValueError(f"number of names must be >= {args.min_names}")

    t_date = _parse_date(args.trade_date, date(2026, 2, 21))
    init_val_date = t_date + timedelta(days=2)
    print("WARNING: NY business-day calendar placeholder uses +2 calendar days.")
    val_date = _parse_date(args.valuation_date, date(2031, 1, 21))

    trade = TradeModel(
        trade_date=t_date,
        initial_valuation_date=init_val_date,
        valuation_date=val_date,
        strike=1.0,
        initial_strategy_value=100.0,
        strategy=StrategyParams(DEFAULT_TARGET_VOL, DEFAULT_LOOKBACK, DEFAULT_STEP_CAP),
        V_millions_range={"min": 300.0, "max": 500.0},
        initial_ec_weights=[WeightItem(ticker=r["ticker"], name=r.get("name") or None, weight=float(r["weight"])) for r in rows],
    )
    write_json(args.out, trade.model_dump())


def build_market_cmd(args: argparse.Namespace) -> None:
    rows = read_market_excel(args.market_xlsx)
    equities = [
        EquityMarketItem(
            ticker=r["ticker"],
            spot=float(r["spot"]),
            atm_vol=_normalize_rate_col(float(r["atm_vol"])),
            div_yield=_normalize_rate_col(float(r["div_yield"])),
        )
        for r in rows
    ]
    market = MarketModel(
        equities=equities,
        correlation=CorrelationModel(rho=DEFAULT_RHO),
        rates=RatesModel(sofr_ois_curve=SOFRCurve(zero_rate=args.sofr_flat)),
    )
    write_json(args.out, market.model_dump())


def price_cmd(args: argparse.Namespace) -> None:
    trade_model = TradeModel.model_validate(read_json(args.trade))
    market_model = MarketModel.model_validate(read_json(args.market))
    validate_trade_market(trade_model, market_model, min_names=args.min_names)

    market_model.correlation.rho = args.rho
    market_model.rates.sofr_ois_curve.zero_rate = args.sofr_flat

    result, diagnostics = run_pricing(trade_model, market_model, args.paths, args.seed, args.rho, args.sofr_flat)
    greeks_rows = None
    if args.greeks:
        greeks_rows = compute_greeks(trade_model, market_model, args.paths, args.seed, args.rho, args.sofr_flat, use_crn=True)

    write_pricing_outputs(args.outdir, result, diagnostics, greeks_rows)
    write_manifest(
        args.outdir,
        basket_xlsx=getattr(args, "basket_xlsx", None),
        market_xlsx=getattr(args, "market_xlsx", None),
        trade_json=args.trade,
        market_json=args.market,
        pricing_request_json=getattr(args, "pricing_request_path", None),
        params=vars(args),
        premium_rate=result.premium_rate,
    )


def run_all_cmd(args: argparse.Namespace) -> None:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    check_files = ["trade.json", "market.json", "pricing_request.json", "pricing_result.json", "diagnostics.csv", "run_manifest.json"]
    if args.greeks:
        check_files.append("greeks.csv")
    if not args.overwrite:
        existing = [f for f in check_files if (outdir / f).exists()]
        if existing:
            raise ValueError(f"Refusing to overwrite existing files: {existing}. Use --overwrite.")

    trade_path = outdir / "trade.json"
    market_path = outdir / "market.json"
    req_path = outdir / "pricing_request.json"

    build_trade_cmd(argparse.Namespace(basket_xlsx=args.basket_xlsx, out=trade_path, trade_date=None, valuation_date=None, min_names=args.min_names))
    build_market_cmd(argparse.Namespace(market_xlsx=args.market_xlsx, out=market_path, sofr_flat=args.sofr_flat))

    req = {
        "trade": str(trade_path), "market": str(market_path), "outdir": str(outdir),
        "paths": args.paths, "seed": args.seed, "rho": args.rho, "sofr_flat": args.sofr_flat,
        "v_millions": args.v_millions, "greeks": args.greeks, "min_names": args.min_names,
    }
    write_json(req_path, req)

    price_args = argparse.Namespace(
        trade=trade_path,
        market=market_path,
        outdir=outdir,
        paths=args.paths,
        seed=args.seed,
        rho=args.rho,
        sofr_flat=args.sofr_flat,
        v_millions=args.v_millions,
        greeks=args.greeks,
        min_names=args.min_names,
        basket_xlsx=args.basket_xlsx,
        market_xlsx=args.market_xlsx,
        pricing_request_path=req_path,
    )
    price_cmd(price_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pricer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_trade = sub.add_parser("build-trade")
    p_trade.add_argument("--basket-xlsx", required=True)
    p_trade.add_argument("--out", required=True)
    p_trade.add_argument("--trade-date", default=None)
    p_trade.add_argument("--valuation-date", default=None)
    p_trade.add_argument("--min-names", type=int, default=50)
    p_trade.set_defaults(func=build_trade_cmd)

    p_mkt = sub.add_parser("build-market")
    p_mkt.add_argument("--market-xlsx", required=True)
    p_mkt.add_argument("--out", required=True)
    p_mkt.add_argument("--sofr-flat", type=float, default=DEFAULT_SOFR)
    p_mkt.set_defaults(func=build_market_cmd)

    p_price = sub.add_parser("price")
    p_price.add_argument("--trade", required=True)
    p_price.add_argument("--market", required=True)
    p_price.add_argument("--outdir", default="outputs")
    p_price.add_argument("--paths", type=int, default=DEFAULT_PATHS)
    p_price.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p_price.add_argument("--rho", type=float, default=DEFAULT_RHO)
    p_price.add_argument("--sofr-flat", type=float, default=DEFAULT_SOFR)
    p_price.add_argument("--v-millions", type=float, default=400.0)
    p_price.add_argument("--greeks", dest="greeks", action="store_true")
    p_price.add_argument("--no-greeks", dest="greeks", action="store_false")
    p_price.set_defaults(greeks=True)
    p_price.add_argument("--min-names", type=int, default=50)
    p_price.set_defaults(func=price_cmd)

    p_all = sub.add_parser("run-all")
    p_all.add_argument("--basket-xlsx", required=True)
    p_all.add_argument("--market-xlsx", required=True)
    p_all.add_argument("--outdir", default="outputs")
    p_all.add_argument("--sofr-flat", type=float, default=DEFAULT_SOFR)
    p_all.add_argument("--rho", type=float, default=DEFAULT_RHO)
    p_all.add_argument("--paths", type=int, default=DEFAULT_PATHS)
    p_all.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p_all.add_argument("--v-millions", type=float, default=400.0)
    p_all.add_argument("--greeks", dest="greeks", action="store_true")
    p_all.add_argument("--no-greeks", dest="greeks", action="store_false")
    p_all.set_defaults(greeks=True)
    p_all.add_argument("--min-names", type=int, default=50)
    p_all.add_argument("--overwrite", action="store_true")
    p_all.set_defaults(func=run_all_cmd)
    return parser


def app() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
