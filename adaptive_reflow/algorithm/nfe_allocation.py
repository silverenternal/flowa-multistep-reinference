"""Per-round NFE allocation helpers (Wave 35 FIX-3).

The framework's re-inference loop spends a total NFE budget across
``n_rounds`` rounds. Historically every consumer split that budget
*uniformly* (``tools/run_controlled_audit.py::_nfe_steps_per_round``),
which is the wrong shape for a schedule whose per-round implicit noise
scale ``eps`` declines monotonically:

* round ``0`` runs at the largest ``eps`` — the population is dominated
  by fresh noise, so extra integration steps buy little;
* the terminal rounds run at the smallest ``eps`` — this is where the
  trajectory is being *refined* onto the sheet, and where an extra step
  is worth the most (paper Theorem 1's ``eps -> 0`` limit selects the
  sheet).

Three independent 2026 sources converge on the same prescription:

* ``docs/audit/algorithm-saturation-review.md`` Finding 14 / R2 — the
  codimension scheduler already publishes ``eps_per_round`` on every
  ``ScheduleSample``, and no consumer reads it;
* ``docs/audit/web-research-saturation-2026.md`` Rec 2 — CACFM's
  U-shaped difficulty profile (arXiv:2606.22394) says sampling density
  belongs at the boundary stages, not the middle;
* ``docs/audit/web-research-fm-restart-2026.md`` F-12 — ECT's
  progressive-approximation ramp (arXiv:2410.11046).

:func:`nfe_steps_for_evidence` implements the allocation. It is a pure
function of its arguments — no scheduler state, no randomness — and it
preserves the matched-NFE contract exactly: the returned steps sum to
``nfe`` and every round receives at least one step.
"""

from __future__ import annotations

import math

__all__ = ["nfe_steps_for_evidence", "nfe_steps_uniform"]


def nfe_steps_uniform(nfe: int, n_rounds: int) -> list[int]:
    """Split ``nfe`` steps uniformly across ``n_rounds`` (ceil + carry).

    The legacy allocation, kept here so both policies live in one
    module and a caller can switch between them by name.

    :param nfe: total integration steps to distribute (``>= 1``).
    :param n_rounds: number of rounds (``>= 1``).
    :returns: ``n_rounds`` positive ints summing to ``nfe``; the first
        ``nfe % n_rounds`` rounds carry the remainder.
    :raises ValueError: on ``nfe < 1``, ``n_rounds < 1`` or
        ``nfe < n_rounds`` (a round cannot receive zero steps).

    >>> nfe_steps_uniform(50, 5)
    [10, 10, 10, 10, 10]
    >>> nfe_steps_uniform(12, 5)
    [3, 3, 2, 2, 2]
    """
    nfe, n_rounds = _validate_budget(nfe, n_rounds)
    base, remainder = divmod(nfe, n_rounds)
    return [base + (1 if i < remainder else 0) for i in range(n_rounds)]


def nfe_steps_for_evidence(
    nfe: int,
    eps_per_round: list[float] | tuple[float, ...],
    *,
    max_weight_ratio: float = 8.0,
) -> list[int]:
    """Allocate ``nfe`` steps inversely to each round's ``eps``.

    Round ``i`` receives a share proportional to ``1 / eps_i``, so the
    small-``eps`` refinement rounds get more steps than the high-noise
    early rounds. The raw shares are then rounded to integers under two
    hard constraints that keep the result a drop-in replacement for
    :func:`nfe_steps_uniform`:

    1. every round gets at least ``1`` step;
    2. the returned steps sum to ``nfe`` exactly (matched-NFE).

    Rounding is deterministic: floor the weighted shares, then hand the
    leftover steps to the rounds with the largest fractional remainders
    (ties broken by round index, so two callers with identical inputs
    always get identical output).

    **Bounded skew.** A raw ``1 / eps`` weighting is unusable against
    :class:`CodimensionSheetScheduler`, whose terminal ``eps`` is
    floored at ``1e-9``: that round's weight would be ~8 orders of
    magnitude above round 0's, so it would absorb the entire budget and
    starve every other round to a single step. The weights are
    therefore clipped to ``[w_min, w_min * max_weight_ratio]``, which
    keeps the allocation monotone in ``eps`` while bounding how much
    more compute the finest round may claim over the coarsest.

    A degenerate ``eps`` vector — all values equal, or any value at or
    below zero / non-finite — falls back to :func:`nfe_steps_uniform`
    rather than raising, so a scheduler that has not populated
    ``eps_per_round`` still yields a valid allocation.

    :param nfe: total integration steps to distribute (``>= 1``).
    :param eps_per_round: per-round implicit noise scale, e.g.
        ``[sample.eps_implicit for sample in samples]`` from
        :class:`CodimensionSheetScheduler`. Length gives ``n_rounds``.
    :param max_weight_ratio: largest allowed ratio between the highest
        and lowest per-round weight (``>= 1``). Default ``8.0``.
    :returns: ``len(eps_per_round)`` positive ints summing to ``nfe``.
    :raises ValueError: on ``nfe < 1``, an empty ``eps_per_round``,
        ``nfe < n_rounds``, or ``max_weight_ratio < 1``.

    >>> nfe_steps_for_evidence(50, [0.05, 0.04, 0.03, 0.02, 0.01])
    [5, 6, 7, 11, 21]
    >>> sum(nfe_steps_for_evidence(50, [0.05, 0.04, 0.03, 0.02, 0.01]))
    50
    >>> nfe_steps_for_evidence(50, [0.05, 0.05, 0.05, 0.05, 0.05])
    [10, 10, 10, 10, 10]
    >>> nfe_steps_for_evidence(50, [0.05, 0.0375, 0.025, 0.0125, 1e-9])
    [4, 5, 6, 12, 23]
    """
    eps_list = list(eps_per_round)
    nfe, n_rounds = _validate_budget(nfe, len(eps_list))
    if (
        isinstance(max_weight_ratio, bool)
        or not isinstance(max_weight_ratio, (int, float))
        or not math.isfinite(float(max_weight_ratio))
        or float(max_weight_ratio) < 1.0
    ):
        raise ValueError(
            f"max_weight_ratio must be a finite number >= 1, got "
            f"{max_weight_ratio!r}"
        )

    weights: list[float] = []
    for value in eps_list:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return nfe_steps_uniform(nfe, n_rounds)
        fv = float(value)
        if not math.isfinite(fv) or fv <= 0.0:
            return nfe_steps_uniform(nfe, n_rounds)
        weights.append(1.0 / fv)

    w_min = min(weights)
    w_max_allowed = w_min * float(max_weight_ratio)
    weights = [min(w, w_max_allowed) for w in weights]

    total = math.fsum(weights)
    if not math.isfinite(total) or total <= 0.0:
        return nfe_steps_uniform(nfe, n_rounds)

    # One step is reserved per round up front, so the floor of every
    # share is >= 1 and constraint (1) holds by construction; the
    # remaining budget is what the evidence weighting distributes.
    spare = nfe - n_rounds
    shares = [w / total * spare for w in weights]
    steps = [1 + int(math.floor(s)) for s in shares]
    leftover = nfe - sum(steps)
    if leftover > 0:
        order = sorted(
            range(n_rounds),
            key=lambda i: (-(shares[i] - math.floor(shares[i])), i),
        )
        for i in order[:leftover]:
            steps[i] += 1
    return steps


def _validate_budget(nfe: int, n_rounds: int) -> tuple[int, int]:
    """Validate a ``(nfe, n_rounds)`` budget pair. Returns the ints."""
    if isinstance(nfe, bool) or not isinstance(nfe, int):
        raise ValueError(f"nfe must be int, got {nfe!r}")
    if isinstance(n_rounds, bool) or not isinstance(n_rounds, int):
        raise ValueError(f"n_rounds must be int, got {n_rounds!r}")
    if int(nfe) < 1:
        raise ValueError(f"nfe must be >= 1, got {nfe!r}")
    if int(n_rounds) < 1:
        raise ValueError(f"n_rounds must be >= 1, got {n_rounds!r}")
    if int(nfe) < int(n_rounds):
        raise ValueError(
            f"nfe must be >= n_rounds so every round gets at least one "
            f"step, got nfe={nfe!r}, n_rounds={n_rounds!r}"
        )
    return int(nfe), int(n_rounds)
