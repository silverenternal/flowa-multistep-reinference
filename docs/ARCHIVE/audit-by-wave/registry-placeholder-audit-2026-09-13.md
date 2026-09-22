# Registry placeholder audit

`adaptive_reflow/writer/registry.py` contains two GraphBFN `TODO:` values: a
checkpoint commit and a license. They are intentional fail-closed metadata,
because the paper/weights acquisition gate has not landed. The corresponding
entry is `adapter_status="unsupported"`; replacing either value with a
fabricated SHA or license would make an unsupported candidate appear
reproducible. No source change was made.

The Wan2.2 SOTA driver has the same explicit dependency gate and returns a
non-zero stub status until weights and reference code are available. These
placeholders are therefore tracked blockers, not accidental implementation
TODOs.

Validation: imported `adaptive_reflow.writer.registry` and inspected the
GraphBFN entry construction without network access or external weights.

