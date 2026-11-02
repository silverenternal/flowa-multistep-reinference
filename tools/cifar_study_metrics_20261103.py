#!/usr/bin/env python3
"""Blocked polynomial MMD U-statistics and replayable per-sample kernel sums."""

from __future__ import annotations

import numpy as np


def kernel_rows(
    x: np.ndarray, y: np.ndarray, *, self_kernel: bool = False, block: int = 128
) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim != 2 or y.ndim != 2 or x.shape[1] != y.shape[1] or min(len(x), len(y)) < 2:
        raise ValueError("need compatible feature matrices with at least two rows")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("nonfinite features")
    if self_kernel and not np.array_equal(x, y):
        raise ValueError("self-kernel must receive identical matrices")
    rows = []
    for start in range(0, len(x), block):
        k = (x[start : start + block] @ y.T / x.shape[1] + 1.0) ** 3
        if self_kernel:
            k[np.arange(len(k)), np.arange(start, start + len(k))] = 0.0
        rows.append(k.sum(axis=1) / (len(y) - int(self_kernel)))
    return np.concatenate(rows)


def kernel_score(xx_rows: np.ndarray, xy_rows: np.ndarray, reference_self: float) -> float:
    if np.shape(xx_rows) != np.shape(xy_rows) or len(xx_rows) < 2:
        raise ValueError("witness row mismatch")
    return float(np.mean(xx_rows) + reference_self - 2 * np.mean(xy_rows))
