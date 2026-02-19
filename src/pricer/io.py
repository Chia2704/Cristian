"""I/O helpers for pseudo-Excel (CSV) and JSON payloads."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REQUIRED_BASKET_COLUMNS = {"ticker", "weight"}
REQUIRED_MARKET_COLUMNS = {"ticker", "spot", "atm_vol", "div_yield"}


def _read_csv_like(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Empty template file")
        rows = []
        for row in reader:
            rows.append({str(k).strip().lower(): str(v).strip() for k, v in row.items()})
        return rows


def read_basket_excel(path: str | Path) -> list[dict[str, str]]:
    rows = _read_csv_like(path)
    if not rows:
        raise ValueError("Basket file is empty")
    missing = REQUIRED_BASKET_COLUMNS - set(rows[0].keys())
    if missing:
        raise ValueError(f"Basket file missing columns: {sorted(missing)}")
    return rows


def read_market_excel(path: str | Path) -> list[dict[str, str]]:
    rows = _read_csv_like(path)
    if not rows:
        raise ValueError("Market file is empty")
    missing = REQUIRED_MARKET_COLUMNS - set(rows[0].keys())
    if missing:
        raise ValueError(f"Market file missing columns: {sorted(missing)}")
    return rows


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with p.open("w", encoding="utf-8") as f:
            f.write("")
        return
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
