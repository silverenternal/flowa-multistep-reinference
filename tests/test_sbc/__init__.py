"""Simulation-Based Calibration (SBC) tests for stochastic re-inference (C.7).

Per Talts et al. 2018 (Stan reference implementation): draw N
``(theta, x)`` pairs with ``theta ~ prior``, ``x ~ p(x|theta)``;
re-infer ``theta_hat``; rank histogram of ``theta_hat`` vs ``theta``
must be approximately uniform for calibrated algorithm. The rank
histogram's chi-squared statistic against the uniform null is the
test statistic; we accept ``p > 0.05`` for a calibrated algorithm.

Wave 18 Phase 2 (C.7) covers the public stochastic algorithms in the
framework:

* :mod:`adaptive_reflow.algorithm.dynamic_noise_bias` —
  :class:`Theorem1DynamicNoiseBias` (eps(r) posterior selection ratio).
* :mod:`adaptive_reflow.algorithm.policy_driver` —
  :class:`AdaptivePolicyDriver` (digest-seeded beta envelope).
* :mod:`adaptive_reflow.algorithm.scheduler_extra` —
  :class:`JitteredConstantScheduler`,
  :class:`MultiChannelJitteredConstantScheduler` (per-round n_cap
  jitter).
* :mod:`adaptive_reflow.adapters.integrators` —
  :class:`EulerMaruyamaIntegrator`,
  :class:`SDEHeunIntegrator` (SDE-style integrators; C.6 deterministic
  integrators are out of scope here).
* :meth:`SchedulerProtocol.inject_noise` (forward-noise injection
  schedule — verified via the cosine family's ``n_cap``-scaled
  Gaussian draw).

Each test is marked ``@pytest.mark.slow`` so the per-PR gate stays
fast (``pytest -m "not slow"`` correctly skips every SBC test). The
nightly CI runner is :mod:`tools.run_sbc_audit`.

References:

* Talts, S., Betancourt, M., Simpson, D., Vehtari, A., & Gelman, A.
  (2018). Validating Bayesian inference algorithms with
  simulation-based calibration. *Annals of Applied Statistics*.
* framework-internal-metrics.md rev 2 §1 C.7 (metric definition).
* todo/algo-improvement-sbc.md (task spec).
"""

__all__: tuple[str, ...] = ()