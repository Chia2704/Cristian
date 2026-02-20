# MVP Monte Carlo Pricer

Python project to price a European call on a volatility-target strategy index, with both CLI and Streamlit GUI workflows.

## Install

```bash
pip install -e .
```

## CLI Commands

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

## Streamlit GUI

Start the GUI with:

```bash
python -m pricer gui
```

In GitHub Codespaces, forward the Streamlit port (default `8501`) and open it in the browser.

### GUI usage

1. Upload `basket.xlsx` and `market.xlsx`.
2. Set parameters (`sofr flat`, `rho`, `paths`, `seed`, `v_millions`, `greeks`, `min-names`).
3. Click **Run Pricing**.
4. View pricing results (`premium_rate`, `premium_per_100`, `stderr_rate`, `stderr_per_100`).
5. View diagnostics and optional Greeks table.
6. Download run artifacts (`pricing_result.json`, `greeks.csv`, `diagnostics.csv`, `run_manifest.json`).

Each GUI run writes files to a run-specific folder: `outputs_gui/<timestamp>/` with uploads saved under `inputs/`.
