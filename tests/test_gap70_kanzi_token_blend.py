"""GAP-70 — Kanzi token-selective latent blend (default off).

Pre-registration and the two premise corrections are in
``docs/audit/gap70-kanzi-latent.md`` §0. That note also records that **K7 is a
LineageFlow cell**, so nothing here can move K7; these tests only establish that
the mechanism is implemented, is off by default, and fails closed.

The operator is ``m_vec = m_base * w`` with ``w`` read per record from
``prior_entry["token_keep_weights"]``. ``w ≡ 1`` must reproduce the scalar blend
exactly, and ``w ≡ 0`` must make the restart independent of the prior.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from adaptive_reflow.adapters.kanzi import (
    AUDIT_KANZI_TOKEN_SELECTIVE_BLEND,
    KANZI_ABSTRACT_AR_SEQ_LENGTH,
    KanziAdapter,
    KanziGPTPriorRestartPolicy,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _adapter(**kwargs: object) -> KanziAdapter:
    return KanziAdapter(force_mode="synthetic", num_steps=2, **kwargs)


def _make_final_policy(*, policy_id: str, beta: float) -> object:
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    channel = ChannelName("protein_latent")
    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-gap70"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _restart(
    adapter: KanziAdapter,
    *,
    beta: float,
    sample_id: str = "s",
    keep: np.ndarray | None = None,
) -> tuple[np.ndarray, object]:
    bundle = adapter.build_initial_state(batch_id="b", sample_id=sample_id)
    if keep is not None:
        entry = adapter._native_states.get(bundle.native_state_digest)
        entry["token_keep_weights"] = np.asarray(keep, dtype=np.float64)
    prior = np.asarray(
        adapter._native_states.get(bundle.native_state_digest)["x0"],
        dtype=np.float64,
    )
    policy = _make_final_policy(policy_id=f"p-{beta}", beta=beta)
    out = adapter.apply_restart_distribution(bundle, policy)
    restarted = np.asarray(
        adapter._native_states.get(out.native_state_digest)["x0"], dtype=np.float64
    )
    return prior, restarted, out


# ---------------------------------------------------------------------------
# 1. default off
# ---------------------------------------------------------------------------


def test_default_off_does_not_read_the_weights_key() -> None:
    """The flag defaults to False and the key is ignored on the default path."""
    adapter = _adapter()
    assert adapter._token_selective_blend is False
    _, restarted, out = _restart(
        adapter, beta=0.5, keep=np.zeros(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    )
    assert np.all(np.isfinite(restarted))
    assert AUDIT_KANZI_TOKEN_SELECTIVE_BLEND not in out.provenance


# ---------------------------------------------------------------------------
# 2. the operator
# ---------------------------------------------------------------------------


def test_uniform_weights_reproduce_the_scalar_blend() -> None:
    """``w ≡ 1`` ⇒ ``m_vec = m_base``, so the two paths must agree bit-for-bit."""
    plain = _adapter()
    selective = _adapter(token_selective_blend=True)
    _, plain_x, _ = _restart(plain, beta=0.5)
    _, sel_x, _ = _restart(
        selective,
        beta=0.5,
        keep=np.ones(KANZI_ABSTRACT_AR_SEQ_LENGTH),
    )
    np.testing.assert_array_equal(plain_x, sel_x)


def test_zero_weights_make_the_restart_prior_independent() -> None:
    """``w ≡ 0`` ⇒ ``m_vec = 0`` ⇒ the output is the fresh draw, whatever the prior.

    Two different priors (different ``sample_id``) restarted with the same
    policy must therefore produce the same tensor.
    """
    selective = _adapter(token_selective_blend=True)
    zeros = np.zeros(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    prior_a, x_a, _ = _restart(
        selective, beta=0.5, sample_id="a", keep=zeros
    )
    prior_b, x_b, _ = _restart(
        selective, beta=0.5, sample_id="b", keep=zeros
    )
    assert not np.allclose(prior_a, prior_b)
    np.testing.assert_array_equal(x_a, x_b)


def test_partial_weights_change_the_result() -> None:
    selective = _adapter(token_selective_blend=True)
    half = np.zeros(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    half[: KANZI_ABSTRACT_AR_SEQ_LENGTH // 2] = 1.0
    _, x_half, _ = _restart(selective, beta=0.5, keep=half)
    _, x_full, _ = _restart(
        selective, beta=0.5, keep=np.ones(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    )
    _, x_zero, _ = _restart(
        selective, beta=0.5, keep=np.zeros(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    )
    assert not np.allclose(x_half, x_full)
    assert not np.allclose(x_half, x_zero)


def test_opt_in_path_is_tagged_in_provenance() -> None:
    selective = _adapter(token_selective_blend=True)
    _, _, out = _restart(
        selective, beta=0.5, keep=np.ones(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    )
    assert AUDIT_KANZI_TOKEN_SELECTIVE_BLEND in out.provenance


# ---------------------------------------------------------------------------
# 3. fail closed
# ---------------------------------------------------------------------------


def test_enabled_without_weights_fails_closed() -> None:
    """GAP-69's lesson: a silent scalar fallback would produce fake evidence."""
    from adaptive_reflow.universal import CapabilityMissingError

    selective = _adapter(token_selective_blend=True)
    with pytest.raises(CapabilityMissingError, match="missing_token_keep_weights"):
        _restart(selective, beta=0.5)


@pytest.mark.parametrize(
    ("keep", "code"),
    [
        (np.ones(KANZI_ABSTRACT_AR_SEQ_LENGTH - 1), "wrong_length"),
        (np.full(KANZI_ABSTRACT_AR_SEQ_LENGTH, 1.5), "out_of_unit_interval"),
        (np.full(KANZI_ABSTRACT_AR_SEQ_LENGTH, -0.1), "out_of_unit_interval"),
        (np.full(KANZI_ABSTRACT_AR_SEQ_LENGTH, np.nan), "nonfinite"),
    ],
)
def test_malformed_weights_are_rejected(keep: np.ndarray, code: str) -> None:
    from adaptive_reflow.universal import CapabilityMissingError

    selective = _adapter(token_selective_blend=True)
    with pytest.raises(CapabilityMissingError, match=code):
        _restart(selective, beta=0.5, keep=keep)


def test_mutually_exclusive_with_the_gpt_prior_policy() -> None:
    with pytest.raises(ValueError, match="mutually_exclusive"):
        _adapter(
            token_selective_blend=True,
            gpt_prior_restart_policy=KanziGPTPriorRestartPolicy(),
        )
