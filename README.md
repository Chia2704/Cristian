# MVP Monte Carlo Pricer

CLI-only Python project to price a European call on a volatility-target strategy index.

## Install

```bash
pip install -e .
```

## Commands

```bash
python -m pricer build-trade --basket-xlsx template_basket.xlsx --out outputs/trade.json
python -m pricer build-market --market-xlsx template_market.xlsx --out outputs/market.json
python -m pricer price --trade outputs/trade.json --market outputs/market.json --outdir outputs
python -m pricer run-all --basket-xlsx template_basket.xlsx --market-xlsx template_market.xlsx --outdir outputs --overwrite
```

Defaults:
- `paths=10000`
- `seed=42`
- `rho=0.8`
- `sofr_flat=0.0366`
- `target_vol=0.10`
- `lookback_bd=40`
- `exposure_step_cap=0.20`

For demo templates with 2 names, use `--min-names 2`.
