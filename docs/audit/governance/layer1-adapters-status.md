# Wave 101 Layer-1 adapter status audit

The planned P0 hygiene is already present: HiDream uses `NativeStateCache`,
shared seed/digest/reference helpers are available in `_adapter_common`, and
weight-path wrappers delegate to `resolve_candidate_paths`. The shared
`_resolve_mode` helper also exists (Wave 103), although several adapters retain
local mode ladders with adapter-specific error sentinels; replacing those
would exceed a safe mechanical change without per-adapter contract tests.

Focused adapter validation passed **32 tests** (3 warnings); 5 integration tests
were skipped because torch/transformers are unavailable. No adapter behavior or
GPU path was changed in this pass.
