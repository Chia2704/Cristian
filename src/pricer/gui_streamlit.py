"""Streamlit GUI for running the pricer run-all pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

import pandas as pd
import streamlit as st

from pricer.cli import DEFAULT_PATHS, DEFAULT_RHO, DEFAULT_SEED, DEFAULT_SOFR, run_all_pipeline


def _timestamped_run_dir() -> Path:
    return Path("outputs_gui") / datetime.now().strftime("%Y%m%d_%H%M%S")


def _save_uploaded_file(upload, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(upload.getbuffer())


def _file_download(label: str, path: Path, mime: str) -> None:
    if path.exists():
        st.download_button(label=label, data=path.read_bytes(), file_name=path.name, mime=mime)


def main() -> None:
    st.set_page_config(page_title="MVP Monte Carlo Pricer", layout="centered")
    st.title("MVP Monte Carlo Pricer")

    basket_file = st.file_uploader("Upload basket.xlsx", type=["xlsx"])
    market_file = st.file_uploader("Upload market.xlsx", type=["xlsx"])

    col1, col2 = st.columns(2)
    with col1:
        sofr_flat = st.number_input("SOFR flat", value=float(DEFAULT_SOFR), format="%.6f")
        rho = st.number_input("rho", value=float(DEFAULT_RHO), min_value=-1.0, max_value=1.0, format="%.4f")
        paths = st.number_input("paths", value=int(DEFAULT_PATHS), min_value=100, step=1000)
        seed = st.number_input("seed", value=int(DEFAULT_SEED), step=1)
    with col2:
        v_millions = st.number_input("v_millions", value=400.0, min_value=0.0, step=10.0)
        min_names = st.number_input("min-names", value=50, min_value=1, step=1)
        greeks = st.checkbox("Compute Greeks", value=True)

    if st.button("Run Pricing"):
        if basket_file is None or market_file is None:
            st.error("Please upload both basket.xlsx and market.xlsx before running.")
            return

        run_dir = _timestamped_run_dir()
        inputs_dir = run_dir / "inputs"
        basket_path = inputs_dir / "basket.xlsx"
        market_path = inputs_dir / "market.xlsx"
        _save_uploaded_file(basket_file, basket_path)
        _save_uploaded_file(market_file, market_path)

        try:
            with st.spinner("Running pricing..."):
                run_all_pipeline(
                    basket_xlsx=basket_path,
                    market_xlsx=market_path,
                    outdir=run_dir,
                    sofr_flat=float(sofr_flat),
                    rho=float(rho),
                    paths=int(paths),
                    seed=int(seed),
                    v_millions=float(v_millions),
                    greeks=bool(greeks),
                    min_names=int(min_names),
                    overwrite=True,
                )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Run failed: {exc}")
            return

        st.success(f"Run completed: {run_dir}")

        pricing_result_path = run_dir / "pricing_result.json"
        diagnostics_path = run_dir / "diagnostics.csv"
        greeks_path = run_dir / "greeks.csv"
        manifest_path = run_dir / "run_manifest.json"

        if pricing_result_path.exists():
            pricing = json.loads(pricing_result_path.read_text())
            st.subheader("Pricing")
            st.write({
                "premium_rate": pricing.get("premium_rate"),
                "premium_per_100": pricing.get("premium_per_100"),
                "stderr_rate": pricing.get("stderr_rate"),
                "stderr_per_100": pricing.get("stderr_per_100"),
            })

        if diagnostics_path.exists():
            diagnostics_df = pd.read_csv(diagnostics_path)
            st.subheader("Diagnostics")
            st.dataframe(diagnostics_df, use_container_width=True)

        if greeks and greeks_path.exists():
            st.subheader("Greeks")
            st.dataframe(pd.read_csv(greeks_path), use_container_width=True)

        st.subheader("Downloads")
        _file_download("Download pricing_result.json", pricing_result_path, "application/json")
        _file_download("Download diagnostics.csv", diagnostics_path, "text/csv")
        _file_download("Download run_manifest.json", manifest_path, "application/json")
        _file_download("Download greeks.csv", greeks_path, "text/csv")


if __name__ == "__main__":
    main()
