# Wave 129 EvidenceDriven / FreeTraj blocker audit

The incomplete N=16 run was not an unbounded loop. The driver executes each
framework arm serially over `framework_samples × n_rounds × num_steps`; with
NFE=50 and four rounds this is a deliberately expensive forward workload.

A bounded smoke (`n_samples=2`, `framework_samples=2`, one round, one step)
completed both `EvidenceDrivenScheduler` and `FreeTrajScheduler` successfully
on GPU0. FID was skipped because `data/cifar10_test_ref.npz` is absent. No
code change was necessary; the prior stall was compute duration, not a
scheduler deadlock. Full metrics remain incomplete and no paper claim was
updated.
