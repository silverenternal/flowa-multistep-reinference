# Wave 101 Layer-3 P1-B large adapter-test audit

Date: 2026-09-13. Reviewed the five model-specific adapter test modules over
1000 LOC (`twodim_fm`, FlowMol3, FlowMol3 v2, Rectified Flow CIFAR, and
Kanzi). `test_protocol_deep_audit.py` is a shared cross-adapter battery and
was handled under P1-A.

No safe split was identified: each large module groups constructor fixtures,
capability checks, protocol conformance, and byte-stability assertions around
the same adapter fixtures. Moving classes or helpers would require changing
module-scoped fixtures and risks import/collection semantics. The result is
audit-only, preserving test names and behavior.

Per-file collection counts are 17, 73, 21, 26, and 26 respectively; the
aggregate adapter-suite baseline remains 1264 tests. Focused runtime checks:

```
pytest -q tests/test_adapters/test_twodim_fm.py \
  tests/test_adapters/test_rectified_flow_cifar.py
42 passed, 1 skipped (torch unavailable)
```

No D.4 files or production code were changed.
