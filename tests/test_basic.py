"""Basic integration tests for CLI workflow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_all_deterministic(tmp_path: Path) -> None:
    """Run full pipeline and verify deterministic premium with fixed seed."""
    repo_root = Path(__file__).resolve().parents[1]
    basket = repo_root / "template_basket.xlsx"
    market = repo_root / "template_market.xlsx"

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    cmd1 = [
        sys.executable,
        "-m",
        "pricer",
        "run-all",
        "--basket-xlsx",
        str(basket),
        "--market-xlsx",
        str(market),
        "--min-names",
        "2",
        "--outdir",
        str(out1),
        "--overwrite",
        "--no-greeks",
    ]
    cmd2 = cmd1.copy()
    cmd2[cmd2.index(str(out1))] = str(out2)

    subprocess.run(cmd1, check=True, env=env)
    subprocess.run(cmd2, check=True, env=env)

    r1_path = out1 / "pricing_result.json"
    r2_path = out2 / "pricing_result.json"
    assert r1_path.exists()
    assert r2_path.exists()

    r1 = json.loads(r1_path.read_text(encoding="utf-8"))
    r2 = json.loads(r2_path.read_text(encoding="utf-8"))

    assert isinstance(r1["premium_rate"], float)
    assert abs(r1["premium_rate"] - r2["premium_rate"]) <= 1e-12
