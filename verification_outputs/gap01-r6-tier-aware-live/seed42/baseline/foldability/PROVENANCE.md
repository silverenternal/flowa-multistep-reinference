# seed42 baseline fold — reused from the frozen Wave 161 fold

`seed42/fasta/baseline.fasta` is **byte-identical** to the frozen Wave 161
baseline (`verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta`,
verified sequence-by-sequence), because the baseline arm's RNG is seeded with
`--seed` and the frozen baseline was generated at seed 42. The frozen
`foldability.jsonl` is therefore the correct seed-42 baseline fold and is
copied here so the within-seed pairing uses one uniform path.

Seeds 43 and 44 draw **different** baseline sequences (`random.Random(seed)`),
so their baselines are folded fresh under this directory's siblings.
