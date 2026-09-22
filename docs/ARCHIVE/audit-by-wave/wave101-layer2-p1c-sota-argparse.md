# Wave 101 Layer 2 P1-C: SOTA CLI audit

**Date:** 2026-09-13  
**Scope:** `tools/run_sota_*.py` command-line parsers  
**Decision:** audit-only; defer shared extraction

The repository currently contains **nine** SOTA drivers (the plan's estimate
of eight is stale). Their parser blocks are local to each driver and expose
different option names, defaults, enum choices, and output semantics. The
smallest commonality is `--help` plumbing, which does not justify a shared
module or an adapter layer. Extracting options would either change help text
and defaults or require a compatibility shim larger than the duplicated code.

Observed parser entry points:

* `run_sota_2d_experiment.py`
* `run_sota_cifar_experiment.py`
* `run_sota_comparison.py` (`_build_parser`)
* `run_sota_flowmol3_v2_adapter_experiment.py`
* `run_sota_graphbfn_experiment.py`
* `run_sota_hidream_i1_experiment.py`
* `run_sota_lumina_image_2_0_experiment.py`
* `run_sota_protbfn_abbfn_adapter_experiment.py`
* `run_sota_wan2_2_video_experiment.py`

## Verification

From repository root at commit `f42de22`, each driver was invoked with
`python tools/run_sota_*.py --help`. All nine exited successfully. The only
output was the pre-existing deprecation warning from
`run_sota_comparison.py`; no parser error occurred.

## Follow-up

Keep the parsers local until a common option schema is designed and captured
in a separate proposal. This preserves CLI compatibility and avoids changing
research launch commands during Wave 101 hygiene work.

