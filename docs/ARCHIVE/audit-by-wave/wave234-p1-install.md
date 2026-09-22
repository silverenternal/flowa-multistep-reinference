# Wave 234 P1 — Statistical package install + equivalence primitives

**Audit doc for the Wave 234 P1 stats-package install agent.**

## Scope

Install statistical packages needed for the framework's TPAMI
equivalence claims (TOST, Jonckheere-Terpstra, random-effects
meta-analysis, paired Bayes factor ``BF01``) and provide a pure-NumPy /
SciPy fallback for every procedure so the framework's byte-stable
audit gate continues to run on minimal environments.

## Environment (Wave 234 P1 host)

| Package       | Status        | Version | Notes                            |
| ------------- | ------------- | ------- | -------------------------------- |
| `scipy`       | pre-installed | 1.18.1  | `.venvs/lineageflow_venv`        |
| `numpy`       | pre-installed | 2.5.2   | `.venvs/lineageflow_venv`        |
| `pandas`      | pre-installed | 3.0.5   | `.venvs/lineageflow_venv`        |
| `pingouin`    | installed     | 0.6.1   | pip-installed                    |
| `statsmodels` | installed     | 0.15.0  | pip-installed (pulled by pingouin)|

Both `pingouin` and `statsmodels` install cleanly via
`pip install` in the `lineageflow_venv`; they are exposed in the
runtime as optional backends (`has_pingouin()`, `has_statsmodels()`)
but **all fallbacks are also pure NumPy/SciPy**, so the framework's
audit gate does not require them.

## Fallback implementation

`adaptive_reflow/stats/equivalence.py` provides five procedures with
matching dataclass return types:

| Procedure                    | Function                                   | Result dataclass        |
| ---------------------------- | ------------------------------------------ | ----------------------- |
| TOST (paired)                | `tost_paired(diff, sd, n, margin)`         | `EquivalenceResult`     |
| Non-inferiority (one-sided)  | `non_inferiority(diff, sd, n, margin, direction)` | `NonInferiorityResult` |
| Paired BF01 (BIC / Wagenmakers 2007) | `bf01_paired(diff, n, sd=None)`     | `BayesFactorResult`     |
| DerSimonian-Laird random effects | `meta_random_effects(d_values, se_values)` | `MetaAnalysisResult`  |
| Jonckheere-Terpstra trend    | `jonckheere_terpstra(groups, n_permutations=0, seed=0)` | `JonckheereResult` |

The package re-exports them from `adaptive_reflow.stats` for ergonomic
import (`from adaptive_reflow.stats import tost_paired`).

### Implementation notes

- **`tost_paired`** — uses both one-sided tests with the upper-tail
  survival `scipy.stats.t.sf`; the equivalence decision is the **max**
  of the two p-values being below ``alpha``.
- **`non_inferiority`** — same survival-function convention as TOST
  for both `direction="lower"` and `direction="upper"`.
- **`bf01_paired`** — BIC approximation
  `BF01 ≈ sqrt(n) * (1 + t^2/(n-1))^(-n/2)`. Handles zero-variance
  differences (`sd = inf`, `t = 0`, `BF01 = sqrt(n)`).
- **`meta_random_effects`** — fixed-effect weights → Cochran's Q →
  DerSimonian-Laird ``tau^2`` (clipped at 0) → random-effects pooled
  effect with 95% CI. Reports ``I^2`` (Higgins & Thompson 2002) and
  Q-p. Validates that all SEs are strictly positive.
- **`jonckheere_terpstra`** — pure-Python implementation using
  ``scipy.stats.rankdata`` for tie-aware ranking and the standard
  variance correction for ties. Permutation p-value is optional
  (off by default) and uses ``numpy.random.default_rng(seed)`` for
  byte-stability.

## Tests

`tests/test_stats_equivalence.py` — 16 unit tests, **all PASS**:

```
tests/test_stats_equivalence.py::test_tost_paired_rejects_when_inside_equivalence_window PASSED
tests/test_stats_equivalence.py::test_tost_paired_fails_when_outside_equivalence_window PASSED
tests/test_stats_equivalence.py::test_tost_paired_rejects_invalid_margin PASSED
tests/test_stats_equivalence.py::test_bf01_paired_null_with_large_n_yields_large_bf01 PASSED
tests/test_stats_equivalence.py::test_bf01_paired_alt_with_large_t_yields_small_bf01 PASSED
tests/test_stats_equivalence.py::test_bf01_paired_zero_variance_degenerate PASSED
tests/test_stats_equivalence.py::test_meta_random_effects_recovers_pooled_on_uniform_dataset PASSED
tests/test_stats_equivalence.py::test_meta_random_effects_heterogeneity_signals_positive_tau2 PASSED
tests/test_stats_equivalence.py::test_meta_random_effects_rejects_zero_se PASSED
tests/test_stats_equivalence.py::test_jonckheere_terpstra_strictly_increasing_rejects_null PASSED
tests/test_stats_equivalence.py::test_jonckheere_terpstra_balanced_groups_shows_no_trend PASSED
tests/test_stats_equivalence.py::test_jonckheere_terpstra_requires_two_groups PASSED
tests/test_stats_equivalence.py::test_non_inferiority_rejects_when_difference_well_above_margin PASSED
tests/test_stats_equivalence.py::test_non_inferiority_fails_when_difference_below_minus_margin PASSED
tests/test_stats_equivalence.py::test_non_inferiority_upper_direction PASSED
tests/test_stats_equivalence.py::test_pingouin_and_statsmodels_probes_return_bool PASSED
======================== 16 passed, 3 warnings in 1.83s ========================
```

Each test exercises a known-answer case (textbook equivalence, true-
null Bayes factor, monotone Jonckheere trend, fixed-effect meta
uniform-pooled estimate).

## D.4 byte-stable regression (HARD gate)

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 20.47s
```

D.4 remains **30/30 PASS** after Wave 234 P1 — adding the new
`stats` sub-package and the new test file does not perturb the
existing regression vectors.

## Files touched

| Path                                                | Change                       |
| --------------------------------------------------- | ---------------------------- |
| `adaptive_reflow/stats/__init__.py`                 | new — public re-exports      |
| `adaptive_reflow/stats/equivalence.py`              | new — TOST / NI / BF01 / DL / JT |
| `tests/test_stats_equivalence.py`                   | new — 16 unit tests          |
| `docs/audit/wave234-p1-install.md`                  | new — this audit doc         |

## Backends discovered at runtime

```python
>>> from adaptive_reflow.stats import has_pingouin, has_statsmodels
>>> has_pingouin()
True
>>> has_statsmodels()
True
```

Both are available in the active venv; the framework continues to
default to the pure-NumPy/SciPy fallbacks so the audit gate is
environment-independent.

## Status

- `pingouin_installed`: **true**
- `statsmodels_installed`: **true**
- `fallback_impl_path`: **`adaptive_reflow/stats/equivalence.py`**
- `unit_tests_pass`: **true** (16/16)
- `d4_pass`: **true** (30/30)
- `audit_doc_path`: **`docs/audit/wave234-p1-install.md`**