"""CLM-030: MeanFlowMergeOperator (arXiv:2505.13447) registered as a plug-in merge operator.

Asserted by docs/CLAIMS.md:717-746.
The class `MeanFlowMergeOperator` is registered under the key `"meanflow"`
in the merge-operator registry.

We pin:
    1. The class is importable.
    2. The PROTOCOL_REGISTRY exposes the family key `meanflow`.
"""
from __future__ import annotations

from adaptive_reflow.algorithm.merge_operator_v3 import MeanFlowMergeOperator
from tests.test_claims._claim_template import registered_families


def test_claim_030_meanflow_class_importable() -> None:
    assert MeanFlowMergeOperator is not None

def test_claim_030_meanflow_in_protocol_registry() -> None:
    families = registered_families()
    assert "meanflow" in families.get("MergeOperatorProtocol", ())

def test_claim_030_meanflow_conforms_to_merge_protocol() -> None:
    """Every MergeOperatorProtocol method is present on the class."""
    for method in ("merge", "config_hash", "to_config", "from_config"):
        assert hasattr(MeanFlowMergeOperator, method), f"missing {method}"
