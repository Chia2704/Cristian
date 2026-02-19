"""Output writing and manifest utilities."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pricer.io import write_csv, write_json
from pricer.models import PricingResult
from pricer.pricer import RunDiagnostics


def _module_version(name: str) -> str:
    try:
        mod = __import__(name)
        return str(getattr(mod, "__version__", "unknown"))
    except Exception:
        return "unavailable"


def sha256_file(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_pricing_outputs(outdir: str | Path, pricing_result: PricingResult, diagnostics: RunDiagnostics, greeks_rows: list[dict[str, Any]] | None) -> None:
    p = Path(outdir)
    p.mkdir(parents=True, exist_ok=True)
    write_json(p / "pricing_result.json", pricing_result.model_dump())
    write_csv(p / "diagnostics.csv", [{
        "avg_exposure": diagnostics.avg_exposure,
        "min_exposure": diagnostics.min_exposure,
        "max_exposure": diagnostics.max_exposure,
        "avg_sigma_hat": diagnostics.avg_sigma_hat,
    }])
    if greeks_rows is not None:
        write_csv(p / "greeks.csv", greeks_rows)


def write_manifest(outdir: str | Path, basket_xlsx: str | Path | None, market_xlsx: str | Path | None, trade_json: str | Path | None, market_json: str | Path | None, pricing_request_json: str | Path | None, params: dict[str, Any], premium_rate: float) -> None:
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sha256": {
            "basket_xlsx": sha256_file(basket_xlsx) if basket_xlsx else None,
            "market_xlsx": sha256_file(market_xlsx) if market_xlsx else None,
            "trade_json": sha256_file(trade_json) if trade_json else None,
            "market_json": sha256_file(market_json) if market_json else None,
            "pricing_request_json": sha256_file(pricing_request_json) if pricing_request_json else None,
        },
        "package_versions": {
            "numpy": _module_version("numpy"),
            "pandas": _module_version("pandas"),
            "pydantic": _module_version("pydantic"),
            "typer": _module_version("typer"),
        },
        "parameters": params,
        "summary": f"premium_rate={premium_rate}",
    }
    write_json(Path(outdir) / "run_manifest.json", manifest)
