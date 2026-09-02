"""SOTA protein-sequence BFN experiment harness (R16 - real ProtBFN / AbBFN).

Drives the :class:`adaptive_reflow.adapters.protbfn_abbfn_adapter
.ProtBFNAbBFNAdapter` end-to-end against the **real** InstaDeep
ProtBFN / AbBFN checkpoints at
``data/protbfn_abbfn/weights_real/{ProtBFN,AbBFN}``. Each round invokes
``Engine.run_round`` which executes the BFN sampling loop (paper
``num_steps`` ~250 for unconditional generation, ~100 for AbBFN
inpainting). Per-round metrics, per-sequence FASTA outputs, and a
JSON summary are emitted under ``--output-dir``.

The harness is intentionally small: it exists to validate the
adapter-to-encoder wire-up, exercise the JAX-free weight loader
against the real ``tree_def.npy`` + ``array_*.npy`` checkpoint, and
produce deterministic per-sequence perplexity and diversity numbers
that a downstream claim script can fold into the comparison.md
five-row table.

CLI
---

::

    python tools/run_sota_protbfn_abbfn_adapter_experiment.py \\
        --weights data/protbfn_abbfn/weights_real/ProtBFN \\
        --model protbfn \\
        --n-samples 8 \\
        --n-rounds 2 \\
        --output-dir /tmp/exp_c_real_protbfn \\
        --seed 0

The default ``--baseline-nfe 250`` matches the paper-reported
unconditional BFN NFE budget. Smaller ``--num-steps`` values speed
up smoke tests at the cost of fidelity.

P-05 (paper-parity FlowA NFE): ``--bfn-steps-per-round`` (default 125)
controls the per-round BFN refinement steps. The default keeps the
total FlowA NFE budget at ``2 rounds * 125 = 250`` (paper parity with
``--baseline-nfe``), preventing the legacy behaviour of dividing the
total budget across rounds (which produced too few steps per round for
the FlowA refiner to converge).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Helpers - amino-acid vocabulary (canonical ProtBFN/AbBFN tokenizer).
# ---------------------------------------------------------------------------

#: 32-entry tokenizer from ``data/protbfn_abbfn/repo/utils.py``. Index 0..5
#: are control tokens (``<unk>``, ``<pad>``, ``<mask>``, ``<cls>``,
#: ``<eos>``, ``<bos>``); 6..31 are amino-acid tokens.
PROTBFN_ID_TO_TOKEN: tuple[str, ...] = (
    "<unk>",
    "<pad>",
    "<mask>",
    "<cls>",
    "<eos>",
    "<bos>",
    "A",
    "R",
    "N",
    "D",
    "C",
    "Q",
    "E",
    "G",
    "H",
    "I",
    "L",
    "K",
    "M",
    "F",
    "P",
    "S",
    "T",
    "W",
    "Y",
    "V",
    "X",
    "B",
    "Z",
    "J",
    "U",
    "O",
)

#: AA token ids 6..31 (the 26 non-control entries).
PROTBFN_AA_TOKEN_IDS: tuple[int, ...] = tuple(range(6, 32))


def sample_to_string(token_ids: np.ndarray) -> str:
    """Convert an array of token ids back to a protein string.

    Mirrors ``data/protbfn_abbfn/repo/utils.py:sample_to_string``.
    Stops at the first EOS (id 4) and skips control tokens (0..5).
    """
    chars: list[str] = []
    for tid in token_ids:
        t = int(tid)
        if t == 4:
            break
        if t > 5:
            chars.append(PROTBFN_ID_TO_TOKEN[t])
    return "".join(chars)


def novelty_vs_set(seq: str, reference: set[str]) -> bool:
    """Return True iff ``seq`` is NOT in the reference set.

    Used for the BFN novelty metric (fraction of generated sequences
    not seen in a held-out reference set). When the reference set is
    empty (no held-out data was supplied) we trivially return True so
    the metric reduces to a count of distinct outputs.
    """
    if not reference:
        return True
    return seq not in reference


def ngram_repetition(sequence: str, n: int = 3) -> float:
    """Return the fraction of ``n``-grams that repeat within ``sequence``.

    ``n=3`` matches the ProtBFN paper's ``repetition_score`` definition
    (count of 3-grams that appear more than once / total 3-grams).
    """
    if len(sequence) < n:
        return 0.0
    grams = [sequence[i : i + n] for i in range(len(sequence) - n + 1)]
    if not grams:
        return 0.0
    counts = Counter(grams)
    repeats = sum(c - 1 for c in counts.values() if c > 1)
    return repeats / len(grams)


def per_sequence_perplexity(
    token_ids: np.ndarray, neg_log_prob: float, length: int
) -> float:
    """Convert a per-sequence negative log-prob into perplexity.

    ``perplexity = exp(-log_prob / length)`` — matches the standard
    ProtBFN paper reporting. ``length`` is the number of *generated*
    tokens (excluding EOS).
    """
    if length <= 0:
        return float("inf")
    return float(np.exp(neg_log_prob / float(length)))


# ---------------------------------------------------------------------------
# Per-round / per-sequence record
# ---------------------------------------------------------------------------


@dataclass
class SequenceRecord:
    """Per-sequence record emitted by the harness."""

    sample_id: str
    round_index: int
    token_ids: list[int]
    sequence: str
    length: int
    perplexity: float
    ngram3_repetition: float
    novelty: bool
    wall_clock_s: float


@dataclass
class RoundRecord:
    """Per-round aggregate emitted by the harness."""

    round_index: int
    n_samples: int
    mean_perplexity: float
    median_perplexity: float
    mean_repetition: float
    novelty_fraction: float
    distinct_sequences: int
    wall_clock_s: float
    sequences: list[SequenceRecord] = field(default_factory=list)


@dataclass
class ExperimentSummary:
    """Top-level experiment summary."""

    model: str
    weights_path: str
    n_samples: int
    n_rounds: int
    num_steps: int
    seed: int
    baseline_nfe: int
    framework_nfe: int
    paired_delta_perplexity: float
    baseline_perplexity: float
    framework_perplexity: float
    rounds: list[RoundRecord]
    model_metadata: dict[str, Any]
    wall_clock_s: float


# ---------------------------------------------------------------------------
# Adapter-driven sampling loop
# ---------------------------------------------------------------------------


def _build_adapter(args: argparse.Namespace) -> Any:
    """Build a :class:`ProtBFNAbBFNAdapter` from CLI args."""
    from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ProtBFNAbBFNAdapter,
    )

    weights_path = Path(args.weights)
    if not weights_path.is_dir():
        raise FileNotFoundError(f"weights_dir_not_found:{weights_path}")
    mechanism = "ProtBFN" if args.model.lower() == "protbfn" else "AbBFN"
    max_seq_length = 512 if mechanism == "ProtBFN" else 256
    # P-05: per-round BFN steps default to ``--bfn-steps-per-round`` (default
    # 125), which keeps the *total* FlowA NFE at paper-parity
    # (``2 rounds * 125 = 250 = --baseline-nfe``). The legacy
    # ``--num-steps`` flag is retained as a fallback for backward
    # compatibility (kept ``<=0`` semantics for the
    # ``--baseline-nfe`` fall-through path).
    if int(args.bfn_steps_per_round) > 0:
        num_steps = int(args.bfn_steps_per_round)
    elif int(args.num_steps) > 0:
        num_steps = int(args.num_steps)
    else:
        num_steps = int(args.baseline_nfe)

    adapter = ProtBFNAbBFNAdapter(
        checkpoint_path=weights_path,
        mechanism=mechanism,
        force_mode="torch",
        num_steps=num_steps,
        max_seq_length=max_seq_length,
        vocab_size=22,  # engine-level AA channel; model internally uses 32
        seed_offset=int(args.seed),
    )
    # Eagerly load the real weights so the JSON records model metadata.
    adapter._load_model()
    return adapter


def _sample_one_sequence(
    adapter: Any,
    *,
    sample_id: str,
    round_index: int,
    seed: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, float, float]:
    """Sample a single sequence from the BFN encoder.

    Returns ``(token_ids, neg_log_prob, wall_clock_s)``. ``token_ids``
    is the per-position argmax over the BFN final-step categorical.
    ``neg_log_prob`` is the negative log probability of the chosen
    tokens under the final-step ``phi`` (softmax over the encoder
    logits); used to compute per-sequence perplexity.

    The actual sampling loop is driven through ``adapter.solve_ode``
    so the framework's discrete-BFN refiner (the
    ``alpha = (step+1)/num_steps`` Bayesian blend) is exercised
    end-to-end against the real encoder.
    """
    import torch

    t0 = time.perf_counter()
    state = adapter.build_initial_state(
        batch_id=f"round-{round_index}", sample_id=sample_id
    )
    from adaptive_reflow.universal.state import ODEConditionDelta

    delta = ODEConditionDelta(
        delta_spec={"num_steps": int(adapter._num_steps)},
        source="run_sota_protbfn_abbfn",
        target_round=int(round_index),
        calibration_artifact_hash="cal-protbfn-abbfn-v1",
    )
    trace = adapter.solve_ode(state, delta, seed=int(seed))
    endpoint = adapter.observe_endpoint(trace, state)
    # Decode the final categorical to token ids via argmax over the
    # engine's 22-entry surface vocabulary. We pull the final theta
    # from the adapter's native-state cache and map it back to the
    # model's 32-token vocabulary by zero-padding the extra control
    # tokens (engine K=22 < model K=32).
    final_theta = np.asarray(
        adapter._native_states[endpoint.native_state_digest]["theta"],
        dtype=np.float64,
    )  # (L, 22)
    L, K_surface = final_theta.shape
    model_K = 32
    if K_surface < model_K:
        pad = np.zeros((L, model_K - K_surface), dtype=np.float64)
        final_theta_full = np.concatenate([final_theta, pad], axis=1)
    else:
        final_theta_full = final_theta[:, :model_K]
    # Run one more forward pass to get the actual phi logits for the
    # final theta — used to compute perplexity.
    theta_t = torch.as_tensor(final_theta_full, dtype=torch.float32)
    # Mirror the device-move done inside `solve_ode` so the harness's
    # own perplexity forward pass works in GPU mode
    # (`PROTBFN_TORCH_DEVICE=cuda`).
    theta_t = theta_t.to(adapter._torch_device)
    with torch.no_grad():
        logits = adapter._torch_model(theta_t)
    log_probs = torch.log_softmax(logits, dim=-1)
    # Argmax in the model's 32-token space gives the predicted token.
    token_ids = log_probs.argmax(dim=-1).cpu().numpy().astype(np.int64)
    # Perplexity: log probability of the argmax token under phi.
    neg_log_prob = float(
        -log_probs[torch.arange(L), torch.as_tensor(token_ids, dtype=torch.long)]
        .sum()
        .item()
    )
    wall_clock = time.perf_counter() - t0
    return token_ids, neg_log_prob, wall_clock


def _run_baseline(
    *,
    adapter: Any,
    n_samples: int,
    num_steps: int,
    seed: int,
    rng: np.random.Generator,
    output_dir: Path,
) -> tuple[float, float, float, list[str], Path]:
    """Trained-model single-pass baseline.

    Runs ``num_steps`` BFN refinement steps (``--baseline-nfe``) using
    the *trained* ProtBFN / AbBFN model already loaded by
    ``adapter`` (not a uniform-categorical reference), and reports the
    mean per-sequence perplexity over ``n_samples`` freshly-sampled
    sequences. Also writes a ``baseline.fasta`` containing the produced
    sequences so the baseline is reproducible from disk.

    Returns ``(baseline_perplexity, baseline_std, baseline_max,
    baseline_sequences, baseline_fasta_path)``.

    The actual sampling loop mirrors :func:`_sample_one_sequence` so
    the trained-model baseline and the multi-round framework run use
    the same per-step encode / Bayesian-update / decode logic.
    """
    import torch

    fasta_path = output_dir / "baseline.fasta"
    seqs: list[str] = []
    perps: list[float] = []
    fasta_lines: list[str] = []
    for sample_idx in range(int(n_samples)):
        sample_id = f"baseline-s{sample_idx}"
        sub_seed = int(seed) * 10_000 + 9000 + int(sample_idx)
        t0 = time.perf_counter()
        state = adapter.build_initial_state(
            batch_id="baseline", sample_id=sample_id
        )
        from adaptive_reflow.universal.state import ODEConditionDelta

        delta = ODEConditionDelta(
            delta_spec={"num_steps": int(num_steps)},
            source="run_sota_protbfn_abbfn_baseline",
            target_round=0,
            calibration_artifact_hash="cal-protbfn-abbfn-baseline-v1",
        )
        trace = adapter.solve_ode(state, delta, seed=int(sub_seed))
        endpoint = adapter.observe_endpoint(trace, state)
        # Decode the final categorical to token ids via argmax over the
        # engine's 22-entry surface vocabulary, padding to the model's
        # 32-token vocabulary before running the encoder for logits.
        final_theta = np.asarray(
            adapter._native_states[endpoint.native_state_digest]["theta"],
            dtype=np.float64,
        )  # (L, 22)
        L_eff, K_surface = final_theta.shape
        model_K = 32
        if K_surface < model_K:
            pad = np.zeros((L_eff, model_K - K_surface), dtype=np.float64)
            final_theta_full = np.concatenate([final_theta, pad], axis=1)
        else:
            final_theta_full = final_theta[:, :model_K]
        theta_t = torch.as_tensor(final_theta_full, dtype=torch.float32)
        # Mirror the device-move done inside `solve_ode` so this baseline
        # forward pass works in GPU mode (`PROTBFN_TORCH_DEVICE=cuda`).
        theta_t = theta_t.to(adapter._torch_device)
        with torch.no_grad():
            logits = adapter._torch_model(theta_t)
        log_probs = torch.log_softmax(logits, dim=-1)
        token_ids = log_probs.argmax(dim=-1).cpu().numpy().astype(np.int64)
        neg_log_prob = float(
            -log_probs[
                torch.arange(L_eff),
                torch.as_tensor(token_ids, dtype=torch.long),
            ]
            .sum()
            .item()
        )
        sequence = sample_to_string(token_ids)
        length = max(1, len(sequence))
        perp = per_sequence_perplexity(token_ids, neg_log_prob, length)
        perps.append(perp)
        seqs.append(sequence)
        fasta_lines.append(
            f">protbfn-abbfn-baseline|sample={sample_id}|seed={sub_seed} "
            f"|perplexity={perp:.3f}|nfe={num_steps}"
        )
        fasta_lines.append(sequence)
        wall = time.perf_counter() - t0
        print(
            f"[protbfn-abbfn] baseline sample {sample_idx + 1}/{n_samples}: "
            f"perp={perp:.3f} len={length} wall={wall:.1f}s",
            file=sys.stderr,
        )
    with fasta_path.open("w") as f:
        f.write("\n".join(fasta_lines) + "\n")
    arr = np.asarray(perps, dtype=np.float64)
    return (
        float(arr.mean()),
        float(arr.std()),
        float(arr.max()),
        seqs,
        fasta_path,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Drive the protein-BFN experiment harness."""
    parser = argparse.ArgumentParser(
        description="Run a ProtBFN / AbBFN SOTA experiment round-trip."
    )
    parser.add_argument(
        "--weights",
        type=str,
        required=True,
        help="Path to a ProtBFN or AbBFN weight directory (containing "
        "tree_def.npy and array_*.npy files).",
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=("protbfn", "abbfn"),
        default="protbfn",
        help="Which checkpoint variant to load (selects max_seq_length).",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=8,
        help="Number of sequences to sample per round (default 8).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=2,
        help="Number of rounds to run (default 2).",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=0,
        help="Discrete-BFN refinement steps per round. If <=0, "
        "falls back to --baseline-nfe. Deprecated: prefer "
        "--bfn-steps-per-round (P-05) for paper-parity NFE "
        "budgeting.",
    )
    parser.add_argument(
        "--bfn-steps-per-round",
        type=int,
        default=125,
        help="P-05: per-round BFN refinement steps (default 125). "
        "Defaults so that ``2 rounds * 125 = 250`` total NFE "
        "matches the paper's single-pass --baseline-nfe budget. "
        "Overrides --num-steps when > 0; set to 0 to disable "
        "the override and fall back to --num-steps / "
        "--baseline-nfe.",
    )
    parser.add_argument(
        "--baseline-nfe",
        type=int,
        default=250,
        help="Paper-reported baseline NFE budget for unconditional "
        "ProtBFN sampling (default 250).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to write FASTA + JSON outputs to.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Master seed for the experiment (default 0).",
    )
    parser.add_argument(
        "--reference-fasta",
        type=str,
        default=None,
        help="Optional path to a reference FASTA used for the novelty "
        "metric. If omitted, novelty is reported as 'distinct / total'.",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=0,
        help="Override the per-mechanism max sequence length (ProtBFN "
        "= 512, AbBFN = 256). 0 = use per-mechanism default.",
    )
    args = parser.parse_args(argv)

    if int(args.n_samples) <= 0:
        raise ValueError("n_samples_must_be_positive")
    if int(args.n_rounds) <= 0:
        raise ValueError("n_rounds_must_be_positive")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Reference set for novelty (optional).
    reference: set[str] = set()
    if args.reference_fasta is not None:
        ref_path = Path(args.reference_fasta)
        if ref_path.is_file():
            try:
                from Bio import SeqIO  # type: ignore[import-not-found]

                for record in SeqIO.parse(str(ref_path), "fasta"):
                    reference.append(str(record.seq))
            except Exception:
                # Fallback: simple parse.
                with ref_path.open("r") as f:
                    for line in f:
                        if line.startswith(">"):
                            continue
                        s = line.strip()
                        if s:
                            reference.add(s)

    print(
        f"[protbfn-abbfn] building adapter (weights={args.weights}, "
        f"model={args.model}, num_steps={args.num_steps or args.baseline_nfe})",
        file=sys.stderr,
    )
    t0 = time.perf_counter()
    adapter = _build_adapter(args)
    model_meta = adapter._real_model_metadata()
    if not model_meta:
        # Real weights failed to load; surface a clear error rather
        # than running the synthetic refiner (which would silently
        # defeat the purpose of this harness).
        raise RuntimeError(
            "real_weights_failed_to_load: adapter fell back to synthetic"
        )
    print(
        f"[protbfn-abbfn] loaded {model_meta['num_params']:,} params",
        file=sys.stderr,
    )

    rng = np.random.default_rng(int(args.seed))
    round_records: list[RoundRecord] = []
    fasta_lines: list[str] = []

    framework_nfe = int(adapter._num_steps) * int(args.n_rounds)
    print(
        f"[protbfn-abbfn] running {args.n_rounds} rounds x {args.n_samples} "
        f"samples (NFE={framework_nfe})",
        file=sys.stderr,
    )

    for round_idx in range(int(args.n_rounds)):
        round_t0 = time.perf_counter()
        seq_records: list[SequenceRecord] = []
        perps_round: list[float] = []
        reps_round: list[float] = []
        novel_count = 0
        distinct: set[str] = set()
        for sample_idx in range(int(args.n_samples)):
            sample_id = f"r{round_idx}-s{sample_idx}"
            sub_seed = (
                int(args.seed) * 10_000
                + int(round_idx) * 1000
                + int(sample_idx)
            )
            token_ids, neg_lp, sample_wall = _sample_one_sequence(
                adapter,
                sample_id=sample_id,
                round_index=round_idx,
                seed=sub_seed,
                rng=rng,
            )
            sequence = sample_to_string(token_ids)
            length = max(1, len(sequence))
            perplexity = per_sequence_perplexity(token_ids, neg_lp, length)
            rep = ngram_repetition(sequence, n=3)
            is_novel = novelty_vs_set(sequence, reference)
            distinct.add(sequence)
            if is_novel:
                novel_count += 1
            perps_round.append(perplexity)
            reps_round.append(rep)
            seq_records.append(
                SequenceRecord(
                    sample_id=sample_id,
                    round_index=round_idx,
                    token_ids=token_ids.tolist(),
                    sequence=sequence,
                    length=int(length),
                    perplexity=float(perplexity),
                    ngram3_repetition=float(rep),
                    novelty=bool(is_novel),
                    wall_clock_s=float(sample_wall),
                )
            )
            fasta_lines.append(
                f">protbfn-abbfn|sample={sample_id}|round={round_idx} "
                f"|perplexity={perplexity:.3f}|repetition={rep:.4f}"
            )
            fasta_lines.append(sequence)
        round_wall = time.perf_counter() - round_t0
        perps_arr = np.asarray(perps_round, dtype=np.float64)
        rep_arr = np.asarray(reps_round, dtype=np.float64)
        round_records.append(
            RoundRecord(
                round_index=round_idx,
                n_samples=int(args.n_samples),
                mean_perplexity=float(perps_arr.mean()),
                median_perplexity=float(np.median(perps_arr)),
                mean_repetition=float(rep_arr.mean()),
                novelty_fraction=float(novel_count) / float(args.n_samples),
                distinct_sequences=int(len(distinct)),
                wall_clock_s=float(round_wall),
                sequences=seq_records,
            )
        )
        print(
            f"[protbfn-abbfn] round {round_idx}: "
            f"mean_perp={perps_arr.mean():.3f} "
            f"mean_rep={rep_arr.mean():.4f} "
            f"novelty={novel_count}/{args.n_samples} "
            f"wall={round_wall:.1f}s",
            file=sys.stderr,
        )

    # Baseline = trained-model single pass with `--baseline-nfe` steps
    # (no framework multi-round refiner). This is the proper paper-
    # comparable reference number, not a uniform-categorical surrogate.
    (
        baseline_perp,
        baseline_std,
        baseline_max,
        _baseline_seqs,
        baseline_fasta_path,
    ) = _run_baseline(
        adapter=adapter,
        n_samples=int(args.n_samples),
        num_steps=int(args.baseline_nfe),
        seed=int(args.seed),
        rng=rng,
        output_dir=output_dir,
    )
    # Framework perplexity = mean of all per-sequence perplexities.
    all_perps = np.asarray(
        [s.perplexity for r in round_records for s in r.sequences],
        dtype=np.float64,
    )
    framework_perp = float(all_perps.mean())
    paired_delta = baseline_perp - framework_perp

    summary = ExperimentSummary(
        model=str(args.model),
        weights_path=str(args.weights),
        n_samples=int(args.n_samples),
        n_rounds=int(args.n_rounds),
        num_steps=int(adapter._num_steps),
        seed=int(args.seed),
        baseline_nfe=int(args.baseline_nfe),
        framework_nfe=int(framework_nfe),
        paired_delta_perplexity=float(paired_delta),
        baseline_perplexity=float(baseline_perp),
        framework_perplexity=float(framework_perp),
        rounds=round_records,
        model_metadata=model_meta,
        wall_clock_s=float(time.perf_counter() - t0),
    )

    # Write outputs.
    fasta_path = output_dir / "samples.fasta"
    with fasta_path.open("w") as f:
        f.write("\n".join(fasta_lines) + "\n")
    json_path = output_dir / "summary.json"

    def _to_jsonable(obj: Any) -> Any:
        if isinstance(obj, (RoundRecord, SequenceRecord, ExperimentSummary)):
            return asdict(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    with json_path.open("w") as f:
        json.dump(_to_jsonable(summary), f, indent=2, default=_to_jsonable)

    print(
        f"[protbfn-abbfn] wrote {fasta_path} ({len(fasta_lines) // 2} seqs) "
        f"and {json_path}",
        file=sys.stderr,
    )
    print(
        f"[protbfn-abbfn] baseline_perplexity={baseline_perp:.3f} "
        f"framework_perplexity={framework_perp:.3f} "
        f"paired_delta={paired_delta:+.3f}",
        file=sys.stderr,
    )
    return 0


__all__: list[str] = ["main", "SequenceRecord", "RoundRecord", "ExperimentSummary"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
