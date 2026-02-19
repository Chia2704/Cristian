"""Monte Carlo path generation using pure Python lists."""

from __future__ import annotations

import math
import random


def constant_corr_matrix(n_assets: int, rho: float) -> list[list[float]]:
    return [[1.0 if i == j else rho for j in range(n_assets)] for i in range(n_assets)]


def cholesky(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    l = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(l[i][k] * l[j][k] for k in range(j))
            if i == j:
                l[i][j] = math.sqrt(max(matrix[i][i] - s, 0.0))
            else:
                l[i][j] = (matrix[i][j] - s) / l[j][j]
    return l


def generate_standard_normals(paths: int, steps: int, n_assets: int, seed: int) -> list[list[list[float]]]:
    rng = random.Random(seed)
    return [[[rng.gauss(0.0, 1.0) for _ in range(n_assets)] for _ in range(steps)] for _ in range(paths)]


def simulate_gbm_paths(
    spots: list[float],
    vols: list[float],
    divs: list[float],
    r: float,
    steps: int,
    dt: float,
    rho: float,
    normals: list[list[list[float]]],
) -> list[list[list[float]]]:
    paths = len(normals)
    n_assets = len(spots)
    l = cholesky(constant_corr_matrix(n_assets, rho))

    s_paths = [[[0.0 for _ in range(n_assets)] for _ in range(steps + 1)] for _ in range(paths)]
    for p in range(paths):
        s_paths[p][0] = list(spots)
        for t in range(steps):
            z = normals[p][t]
            corr_z = [sum(l[i][k] * z[k] for k in range(n_assets)) for i in range(n_assets)]
            for i in range(n_assets):
                drift = (r - divs[i] - 0.5 * vols[i] * vols[i]) * dt
                diff = vols[i] * math.sqrt(dt) * corr_z[i]
                s_paths[p][t + 1][i] = s_paths[p][t][i] * math.exp(drift + diff)
    return s_paths
