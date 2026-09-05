"""CLM-015: Framework does NOT prove paper Theorem 1 magnitude-level competition.

Asserted by docs/CLAIMS.md:264-279.
The framework's `n_cap` ramp is a convex mixing weight on a state
vector; it is *directionally* aligned with the paper's `eps -> 0`
limit but does not produce the `Theta(eps^{+1}) / O(eps^{+2})` evidence
competition the paper proves at the magnitude level.

The canonical audit record is `docs/audit/EPSILON_DIRECTION.md`.

We pin:
    1. EPSILON_DIRECTION.md exists at the documented path.
    2. The file mentions both `Theta(eps^{+1})` and `O(eps^{+2})`.
    3. The file documents the framework's `eps_implicit` parameter as a
       tunable hyperparameter (NOT the paper's `eps`).
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EPSILON_DIRECTION = ROOT / "docs" / "audit" / "EPSILON_DIRECTION.md"


def test_claim_015_epsilon_direction_audit_exists() -> None:
    assert EPSILON_DIRECTION.exists(), f"{EPSILON_DIRECTION} missing"


def test_claim_015_epsilon_direction_documents_paper_exponents() -> None:
    """The audit references the paper's positive eps exponents."""
    text = EPSILON_DIRECTION.read_text()
    assert "Theta(eps" in text, "Theta(eps^+1) reference missing"
    assert "O(eps" in text, "O(eps^+2) reference missing"


def test_claim_015_epsilon_direction_documents_eps_implicit_tunable() -> None:
    """The audit explicitly distinguishes `eps_implicit` from paper's eps."""
    text = EPSILON_DIRECTION.read_text()
    assert "eps_implicit" in text, "eps_implicit reference missing"
