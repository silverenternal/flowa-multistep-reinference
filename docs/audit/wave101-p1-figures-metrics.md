# Wave 101 P1-D/P1-B audit

The five `tools/_make_*.py` utilities do not share a repeated matplotlib
preamble: the SVG utility is dependency-free, while the remaining scripts use
different local imports and plotting setup. Extracting a common module would
therefore add an import layer without removing duplicated behavior, so P1-D is
closed as no-op after inspection.

P1-B is implemented as a compatibility wrapper in
`tools.paper_metrics_kanzi.compute_pb_validity_pct`. It lazily delegates to the
canonical `tools.paper_metrics` implementation, preserving import behavior and
avoiding eager optional dependency loading. The symbol is included in
`__all__`.

Validation: `pytest -q tests/test_tools/test_paper_metrics_kanzi.py` — **11
passed**, 3 warnings.
