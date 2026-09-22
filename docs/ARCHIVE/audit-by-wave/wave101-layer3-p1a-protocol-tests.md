# Wave 101 Layer-3 P1-A protocol-test organization audit

Date: 2026-09-13. The repository already contains the intended independent
cross-adapter surfaces: `tests/test_adapters/conformance_battery.py` is the
single-source conformance battery, while
`tests/test_adapters/test_protocol_deep_audit.py` owns the deeper protocol
checks. No test behavior or D.4 assets were changed.

Baseline collection (`pytest --collect-only -q tests/test_adapters`) recorded
**1264 tests**. The post-audit tree has the same collection count. The shared
battery collects **130 tests** and the deep protocol audit collects **601**;
these files are already independent from model-specific adapter suites, so
extracting additional code would duplicate rather than reduce coverage.

Focused collection completed successfully:

```
pytest --collect-only -q tests/test_adapters/conformance_battery.py  # 130
pytest --collect-only -q tests/test_adapters/test_protocol_deep_audit.py  # 601
```

The conformance battery runtime invocation was started but exceeds the short
interactive execution window because it initializes every registered adapter;
the existing per-adapter suites remain the runtime validation surface.
