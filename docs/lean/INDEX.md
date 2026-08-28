# Lean 4 Formalization Survey: INDEX

Source repo: `/c/Users/31472/codes/noise-selected-rectification-lean/`

This index enumerates every `.lean` file in the Noise-Selected Rectification
formalization repo together with line counts. The Lean code formalizes
selected lemmas of the paper

> Li, "Gaussian Posterior Selection on Noncompact Fibres with Uniformly
> Separated Roots" (2024).

The repo also hosts the FlowA / FlowoE architecture feasibility proof under
`FlowA/`.

All line counts are derived from `find … -exec wc -l {} \;`.

## Totals

| Metric | Value |
| --- | --- |
| Total `.lean` files | **485** |
| Total lines (`.lean` only) | **137,425** |

(The line total excludes the `lakefile.lean` build file: 486 → 485 + 1 build.)

## Top-level `.lean` files (3 files, 2,692 lines)

Three `.lean` files live directly at the repo root (excluding the `FlowA/`, `Research/`, and `scripts/NSRTrustedBoundary.lean` sub-tree which are listed in their own sections below). `README.md` and `todo.json` are non-Lean root files.

| Path (relative to repo root) | Lines | Description |
| --- | --- | --- |
| `FlowAArchitectureProofs.lean` | 1773 | FlowA / FlowoE architecture feasibility contract: inductive types for `MetricFamily`, `FlowChannel`, `MechanismId`, `ExpertId`, `PythonInterfaceId`, etc.; bundles the full architectural boundary (training, inference, channels, mechanisms, expert hooks, channel freeze, metric-family bundles). |
| `lakefile.lean` | 486 | Lake build manifest. Mathlib dep wiring, library targets, proof targets, and the elaborate list of certificate blueprints (`FlowA.CurrentHybridReflowEvidence`, `…CurrentTrainingDataSignificance`, etc.). |
| `scripts/NSRTrustedBoundary.lean` | 433 | NSR trusted-boundary helper (sibling of the top-level files but listed separately because it lives under `scripts/`); declares trusted-threshold constants and supports the boundary module supervised by `FlowAArchitectureProofs`. |

## FlowA/ (4 files, 886 lines)

| Path | Lines | Description |
| --- | --- | --- |
| `FlowA/CurrentHybridReflowEvidence.lean` | 71 | Generated certificate (do not edit) that freezes the recorded reflow probe evidence hashes, panel counts, GNINA split-safety values, and the "current route endpoint panel present" flag. |
| `FlowA/CurrentTrainingDataSignificance.lean` | 81 | Generated certificate that instantiates `TrainingDataCertificate` from the recorded dataset metrics (row counts, scaffold disjointness, family coverage) and proves `current_training_data_has_unknown_pocket_learnability_evidence`, `…is_not_toy_evidence`, `…has_metric_outcome_supervision`. |
| `FlowA/DataSignificance.lean` | 140 | Contract layer: defines `FamilyCoverage`, `TrainingDataCertificate`, `NonToyDataEvidence`, `HasUnknownPocketSplitEvidence`, `HasMetricOutcomeSupervision`, `HasChemistryDiversitySignal`, `HasCleanStructuralEvidence`, `HasMechanismLearningRoute`, `SupportsUnknownPocketFitting`, `ClaimsEmpiricalEndpointSuccess := False` and projection lemmas. |
| `FlowA/HybridReflowEffectiveness.lean` | 594 | Hybrid Flow / Adaptive Reflow effectiveness contracts: one-round-is-one-solve, deterministic-endpoint-change theorems, frozen-observable-cannot-improve-its-metric, proxy-not-order-preserving counterexample, end-to-end-metric-readiness bottleneck, `CertifiedRoundGain` and `protectedHistorical64Snapshot` translation of certificate evidence into `AtLeastPercent` / `ClosesCurrentRawEndpointClaim` statements. |

## Research/CommutatorSafeChannelFreezing/ (6 files, ~570 lines)

| Path | Lines | Description |
| --- | --- | --- |
| `Research/CommutatorSafeChannelFreezing/QFUSAffineCodimTwo.lean` | small | Affine-codim-two quasi-free-unique-solution (QFUS) regime: commutator-safe channel freezing argument restricted to affine degenerate cases. |
| `Research/CommutatorSafeChannelFreezing/QFUSCounterexamples.lean` | small | Counterexample constructions showing where QFUS fails (boundary of commutator-safe channel freezing claim). |
| `Research/CommutatorSafeChannelFreezing/QFUSFourierTorus.lean` | small | QFUS argument for Fourier torus: explicit frequency-amplitude pairings that remain channel-freeze-safe under the displayed commutator bracket. |
| `Research/CommutatorSafeChannelFreezing/QFUSFrequencyAmplitude.lean` | small | Frequency / amplitude trichotomy (companion to `FREQUENCY_AMPLITUDE_TRICHOTOMY.md`); bounds when frequency and amplitude factors commute. |
| `Research/CommutatorSafeChannelFreezing/QFUSNonlinearTorus.lean` | small | Nonlinear-torus QFUS analysis: extends Fourier-torus QFUS to genuine nonlinear perturbations. |
| `Research/CommutatorSafeChannelFreezing/QFUSOrderSensitiveBrackets.lean` | small | Order-sensitive bracket calibration proof that quantifies the safe-freezing budget under iterated commutators (companion to `ORDER_SENSITIVE_BRACKET_CALIBRATION.md`). |

## Research/FlowOEExpertAggregation/ (3 files, ~1,800 lines)

| Path | Lines | Description |
| --- | --- | --- |
| `Research/FlowOEExpertAggregation/SBVC.lean` | 1097 | SBVC (Stability/Boundedness/Variance/Concentration) bundle for expert aggregation: per-expert boundedness, joint integration objective boundary, and concentration lemmas for mixture-of-experts. |
| `Research/FlowOEExpertAggregation/FiniteHorizonPredictiveEntropy.lean` | 469 | Finite-horizon predictive-entropy analysis for FlowoE expert routing: entropy contractions over a finite rollout horizon. |
| `Research/FlowOEExpertAggregation/MinimalPhaseMemory.lean` | medium | Minimal-phase-memory routing contract for expert aggregation; certifies that expert aggregation respects restart memory constraints. |

## Research/StratifiedChemicalTransport/ (8 files)

| Path | Lines | Description |
| --- | --- | --- |
| `Research/StratifiedChemicalTransport/StratifiedChemicalTransport.lean` | medium | Top-level scaffold: imports the seven `Formal/*` modules and defines the public namespace. |
| `Research/StratifiedChemicalTransport/Formal/Counterexamples.lean` | small | Counterexample constructions showing where stratified transport fails. |
| `Research/StratifiedChemicalTransport/Formal/DimensionCollapse.lean` | small | Dimension-collapse scenario: stratified transport cannot maintain codimension. |
| `Research/StratifiedChemicalTransport/Formal/EntropicBranchWall.lean` | small | Entropic branch-wall obstruction: entropy barrier preventing cross-stratum transport. |
| `Research/StratifiedChemicalTransport/Formal/FiniteBranching.lean` | small | Finite branching case of stratified transport. |
| `Research/StratifiedChemicalTransport/Formal/FiniteBranchStability.lean` | small | Stability of the finite branching regime under small perturbations. |
| `Research/StratifiedChemicalTransport/Formal/FiniteTransport.lean` | small | Finite transport assembly theorem. |
| `Research/StratifiedChemicalTransport/Formal/RestrictedTree.lean` | small | Restricted tree hypothesis (uniform bound on out-degree). |

## Research/NoiseSelectedRectification/ (461 files)

This is the bulk of the formalization. Files are grouped below by topical
cluster. Each cluster is preceded by a one-line summary.

### A. Posterior selection assembly (top-level selection theorems)

Theorems that explicitly deliver "countable (or finite) leading-stratum wins
the posterior limit" results.

| Path | Lines | Description |
| --- | --- | --- |
| `…/CountableStratifiedGaussianPosteriorSelection.lean` | 626 | Master countable-stratum selection theorem (see `THEOREM_1_MAPPING.md` for proof-chain citations). |
| `…/FiniteStratifiedGaussianPosteriorSelection.lean` | medium | Finite-stratum algebraic selection law. |
| `…/GaussianPosteriorPolarSelection.lean` | medium | Polar-coordinate instantiation of the finite selection law for the Gaussian-radial-twist. |
| `…/GaussianScheduleSelection.lean` | medium | Schedule selection layer between geometric selection and probability law. |
| `…/JointConditionalVelocitySelection.lean` | medium | Conditional-velocity joint-selection layer (intermediate before probability law). |
| `…/PosteriorMultibranchQuotient.lean` | 393 | Multibranch quotient bound for the posterior (mass redistribution across multiple critical branches). |
| `…/PosteriorSeparationGate.lean` | medium | Separation gate between minimum-codim stratum and the rest. |
| `…/PosteriorWeightedSeparationGate.lean` | medium | Weighted variant of `PosteriorSeparationGate`. |
| `…/RadialPosteriorBranchGate.lean` | medium | Radial-twist branch gate that selects the correct branch under separation hypothesis. |
| `…/ScheduleSelection.lean` | medium | Generic schedule-selection utility module. |

### B. P1 actual-posterior assembly

| Path | Lines | Description |
| --- | --- | --- |
| `…/P1ActualPosteriorAssembly.lean` | 1721 | The P1 actual-posterior assembly: numerator-reassembly, complement decay, posterior convergence (core proof for the P1 limit theorem; see `THEOREM_1_MAPPING.md`). |
| `…/P1ActualEnergyAtlasReassembly.lean` | medium | Energy-atlas reassembly for the P1 actual posterior: links chart geometry to the full posterior. |
| `…/P1CountablePosteriorLaw.lean` | medium | Countable-planar-posterior-law lemma used by the P1 assembly. |
| `…/P1MixedCodimensionPosteriorLaw.lean` | 581 | Mixed-codimension posterior law (combines minimum-codim layer + higher layers). |
| `…/P1MixedCodimensionFullRescaledLaw.lean` | 460 | Full-rescaled-law version (numerator + denominator). |
| `…/P1MixedCodimensionPhysicalAllocation.lean` | 415 | Physical-region allocation of the mixed-codim posterior mass. |
| `…/P1MixedCodimensionRescaledSheet.lean` | 948 | Rescaled-sheet geometry backing the mixed-codim law. |
| `…/P1MixedCodimensionPolynomialWitness.lean` | 1244 | Polynomial witness for the mixed-codim bound (gives the literal coefficient). |
| `…/P1TwoScalePosteriorAssembly.lean` | 411 | Two-scale assembly (microscopic chart + macroscopic tail). |
| `…/P1VariableJacobianPosteriorLaw.lean` | 936 | Variable Jacobian version of the P1 posterior law. |
| `…/P1StratifiedActualPosteriorLaw.lean` | 375 | Stratified version of the actual-posterior law. |
| `…/P1StratifiedTaggedPosteriorLaw.lean` | medium | Tagged-stratum version. |
| `…/P1PlanarPosteriorLaw.lean` | 700 | Planar-codim version of the posterior law. |

### C. P1 atlas / chart / tube mass

Files that establish local chart geometry, atlas covers, and the corresponding
tube-mass estimates that feed the P1 assembly.

| Path | Lines | Description |
| --- | --- | --- |
| `…/P1CertifiedPhysicalAtlasTheorem.lean` | 1569 | The P1 certified physical atlas theorem (overall "fibre and energy identities" certificate for the nonperiodic case). |
| `…/P1CompactGeometry.lean` | medium | Compact-support geometry of the chart family. |
| `…/P1CompactKernelEnvelope.lean` | medium | Compact-kernel envelope: tight Gaussian upper bound on compact charts. |
| `…/P1CountableFiniteNormalTubeMass.lean` | 398 | Countable-planar-tube-mass bound for finite codim normal charts. |
| `…/P1CountableGeneralFiniteNormalTubeMass.lean` | medium | Generalised countable-tube-mass lemma (beyond planar). |
| `…/P1CountableLocalAtlasExtraction.lean` | medium | Local-atlas extraction: how to glue local charts into a global atlas. |
| `…/P1CountablePlanarTubeMass.lean` | 923 | Planar-tube-mass lemma. |
| `…/P1DisjointBaseCellTrace.lean` | medium | Disjoint-base-cell trace lemma (partition of unity on root cells). |
| `…/P1FramedNormalTube.lean` | medium | Framed normal tube: local chart expressed in a normal frame. |
| `…/P1FullRadialTubeLaw.lean` | 482 | Radial-tube-law assembly (used by the radial branch of the theorem). |
| `…/P1GeometricPosteriorLaw.lean` | medium | Geometric-posterior-law intermediate (before reparametrization). |
| `…/P1IntrinsicTubeBudget.lean` | 387 | Intrinsic tube-budget bound (independent of chart choice). |
| `…/P1KernelTangentFibreRecognition.lean` | 653 | Fibre-recognition in the kernel-tangent chart. |
| `…/P1KernelTangentFibreRecognitionAffineWitness.lean` | medium | Affine witness for kernel-tangent fibre recognition. |
| `…/P1LocalNormalChartCoV.lean` | medium | Local-normal-chart change-of-variables (CoV). |
| `…/P1LocalEqualDimFibreTransition.lean` | medium | Local equal-dim fibre-transition lemma. |
| `…/P1ParabolicTubeChart.lean` | 389 | Parabolic-tube chart for the radial-twist fibration. |
| `…/P1PlanarFibreGermFromResidual.lean` | 608 | Planar-fibre germ from the residual coordinate. |
| `…/P1PlanarHausdorffNormalizedTube.lean` | medium | Planar Hausdorff-normalized tube. |
| `…/P1PlanarLevelSetFramedTube.lean` | medium | Planar-level-set framed tube. |
| `…/P1PlanarLevelSetLocalCoV.lean` | medium | Planar-level-set local CoV. |
| `…/P1PlanarObservableSourceBridge.lean` | 598 | Bridge from planar observable to local chart source. |
| `…/P1PlanarObservableTubeLaw.lean` | medium | Planar-observable tube law. |
| `…/P1PlanarScalarNormalFrame.lean` | medium | Planar-scalar normal frame. |
| `…/P1ProjectedFibreCompatibility.lean` | medium | Projected-fibre compatibility (between the rank-projection chart and the fibre). |
| `…/P1ProjectedDerivativeRankChart.lean` | medium | Derivative-rank chart on the projected fibre. |
| `…/P1OrthogonalSubmersionProductChart.lean` | medium | Orthogonal-submersion product chart. |
| `…/P1RadialCircleBranchLaw.lean` | medium | Radial-circle branch law (root-cell limit law). |
| `…/P1RadialComplexityDichotomy.lean` | medium | Radial-complexity dichotomy (clean vs. caustic vs. bad). |
| `…/P1RadialFixedAtlasGeometry.lean` | 383 | Radial fixed-atlas geometry. |
| `…/P1RadialFixedAtlasIntrinsicGq.lean` | medium | Radial fixed-atlas intrinsic Gq bound. |
| `…/P1RadialFixedAtlasLikelihoodEnvelope.lean` | 726 | Radial fixed-atlas likelihood envelope. |
| `…/P1RadialFixedAtlasQuantitativeRemainder.lean` | 739 | Radial fixed-atlas quantitative remainder. |
| `…/P1RadialFixedAtlasSourceDistortion.lean` | medium | Radial fixed-atlas source distortion. |
| `…/P1RadialGeometricBudget.lean` | medium | Radial geometric budget assembly. |
| `…/P1RadialIntrinsicGeometry.lean` | medium | Radial intrinsic geometry (chart-independent). |
| `…/P1RadialLimitingMeasure.lean` | medium | Radial limiting-measure identification. |
| `…/P1RadialLiteralCoareaCoefficient.lean` | medium | Literal coarea coefficient for the radial-twist. |
| `…/P1RadialObservableTubeLaw.lean` | medium | Radial-observable tube law. |
| `…/P1RadialTwoScaleComplement.lean` | medium | Radial two-scale complement. |
| `…/P1RadialUniformNormalEnvelope.lean` | 590 | Radial uniform normal envelope. |
| `…/P1RankSelectedProductChartRegularity.lean` | 481 | Rank-selected product chart regularity. |
| `…/P1RankSelectedProductCoV.lean` | medium | Rank-selected product chart CoV. |
| `…/P1RankSelectedInverseTubeDifferential.lean` | medium | Rank-selected inverse-tube differential. |
| `…/P1RectangularNormalGram.lean` | medium | Rectangular normal-Gram matrix (positive-definiteness). |
| `…/P1SaturatedTubeTrace.lean` | medium | Saturated-tube trace (mass concentration on saturated cells). |
| `…/P1SingleIntegralEnergyAtlasBridge.lean` | medium | Single-integral energy-atlas bridge. |
| `…/P1SmallRadiusIncidenceBudget.lean` | medium | Small-radius incidence budget. |
| `…/P1StratifiedTaggedTopology.lean` | medium | Stratified tagged topology. |
| `…/P1ThreeNormalGaussianMass.lean` | medium | Three-normal Gaussian-mass bound. |
| `…/P1ThreeVariableTwoNormalTube.lean` | medium | Three-variable two-normal tube. |
| `…/P1TwoNormalGaussianMass.lean` | medium | Two-normal Gaussian-mass bound. |
| `…/P1TwoVariableTubeJacobian.lean` | medium | Two-variable tube Jacobian. |
| `…/P1TwoVariableTubeNormalEnvelope.lean` | medium | Two-variable tube normal envelope. |
| `…/P1UniformlySeparatedCleanFibreClass.lean` | medium | Uniformly-separated clean-fibre class. |
| `…/P1VariableJacobianTubeChart.lean` | 757 | Variable Jacobian tube chart. |
| `…/P1MeasurableNormalCoordinates.lean` | medium | Measurable normal coordinates (Borel measurability). |
| `…/P1MixedCodimensionFullRescaledLaw.lean` | medium | Mixed-codim full rescaled law (companion). |
| `…/P1PeriodicCleanFibreClass.lean` | medium | Periodic clean-fibre class. |
| `…/P1PeriodicCleanFibrePhysicalCells.lean` | medium | Periodic clean-fibre physical cells. |
| `…/P1PeriodicCleanFibreSinWitness.lean` | medium | Periodic clean-fibre sin witness. |
| `…/P1PeriodicMixedCodimensionAmbientLaw.lean` | medium | Periodic mixed-codim ambient law. |
| `…/P1PeriodicMixedCodimensionFullRescaledLaw.lean` | 414 | Periodic mixed-codim full rescaled law. |
| `…/P1PeriodicMixedCodimensionGaussianTail.lean` | 967 | Periodic mixed-codim Gaussian tail. |
| `…/P1PeriodicMixedCodimensionPhysicalAllocation.lean` | medium | Periodic mixed-codim physical allocation. |
| `…/P1PeriodicMixedCodimensionPublicationTheorem.lean` | medium | Periodic mixed-codim publication theorem. |
| `…/P1PeriodicMixedCodimensionRescaledSheet.lean` | 624 | Periodic mixed-codim rescaled sheet. |
| `…/P1PeriodicMixedCodimensionSelection.lean` | 371 | Periodic mixed-codim selection. |
| `…/P1PeriodicMixedCodimensionWitness.lean` | medium | Periodic mixed-codim witness. |
| `…/P1PeriodicProfileGeometry.lean` | medium | Periodic-profile geometry. |
| `…/P1PhysicalBaseTraceAdapter.lean` | medium | Physical-base-trace adapter. |
| `…/P1QuadraticNormalEnvelope.lean` | medium | Quadratic-normal envelope. |
| `…/P1BorelOrthonormalNormalFrame.lean` | medium | Borel orthonormal normal frame. |
| `…/P1AllocationTracePartition.lean` | medium | Allocation-trace partition (sums to one). |
| `…/P1CleanFullFibreParametrization.lean` | medium | Clean full-fibre parametrization. |
| `…/P1CleanStratumBorelPivotAtlas.lean` | medium | Clean-stratum Borel pivot atlas. |
| `…/P1CleanStratumLocalGeometry.lean` | medium | Clean-stratum local geometry. |
| `…/P1CleanStratumLocalRecognition.lean` | medium | Clean-stratum local recognition. |
| `…/P1CleanStratumProductTube.lean` | medium | Clean-stratum product tube. |
| `…/P1DerivativeLinkedEnergyAtlasCertificate.lean` | medium | Derivative-linked energy-atlas certificate. |
| `…/P1DerivativeLinkedPhysicalAtlasBridge.lean` | medium | Derivative-linked physical-atlas bridge. |
| `…/P1EnergyGapComplement.lean` | medium | Energy-gap complement (companion to `…/PosteriorTail`). |
| `…/P1EnergyGapGaussianPriorBridge.lean` | medium | Energy-gap / Gaussian-prior bridge. |
| `…/P1EnergyGapPosteriorTail.lean` | medium | Energy-gap posterior tail. |
| `…/P1EscapedNearLevelObstruction.lean` | medium | Escaped-near-level obstruction (companion `…/P2NearLevelGapCounterexample`). |
| `…/P1EscapingPosteriorCounterexample.lean` | medium | Counterexample: posterior that escapes. |
| `…/P1EscapingPosteriorMeasureTightness.lean` | medium | Tightness failure for the escaping-posterior counterexample. |
| `…/P1EscapingPosteriorModel.lean` | medium | Escaping-posterior model (the construction that fails Theorem 1). |
| `…/P1EscapingPosteriorNonTightness.lean` | medium | Non-tightness proof for the escaping counterexample. |
| `…/P1EscapingPosteriorWindows.lean` | 390 | Escaping-posterior windows (specific failure mode). |
| `…/P1EscapingTubeComplexity.lean` | medium | Escaping-tube complexity. |
| `…/P1FiniteDimensionalSubmersionNormal.lean` | medium | Finite-dim submersion normal chart. |
| `…/P1FiniteDimensionalTubeJacobian.lean` | medium | Finite-dim tube Jacobian. |
| `…/P1FiniteNormalAnisotropicQuadraticEnvelope.lean` | medium | Finite-normal anisotropic quadratic envelope. |
| `…/P1FiniteNormalGaussianMass.lean` | medium | Finite-normal Gaussian mass. |
| `…/P1FiniteNormalIntrinsicBudget.lean` | medium | Finite-normal intrinsic budget. |
| `…/P1FiniteNormalQuadraticEnvelope.lean` | medium | Finite-normal quadratic envelope. |
| `…/P1FiniteNormalTube.lean` | medium | Finite-normal tube. |
| `…/P1FiniteNormalTwoScaleAssembly.lean` | medium | Finite-normal two-scale assembly. |
| `…/P1FiniteOutputNormalGram.lean` | medium | Finite-output normal-Gram. |
| `…/P1FourVariableThreeNormalTube.lean` | medium | Four-variable three-normal tube. |
| `…/P1GeneralBorelOrthonormalNormalFrame.lean` | medium | General Borel orthonormal normal frame. |
| `…/P1GeneralFiniteNormalIntrinsicBudget.lean` | medium | General finite-normal intrinsic budget. |
| `…/P1GeneralFiniteNormalTube.lean` | medium | General finite-normal tube. |
| `…/P1GeneralFiniteNormalTwoScaleAssembly.lean` | medium | General finite-normal two-scale assembly. |
| `…/P1GeneralFiniteNormalUniformTightness.lean` | medium | General finite-normal uniform tightness. |
| `…/P1GqIntrinsicCellTail.lean` | medium | Intrinsic-cell tail in the Gq (Gaussian-quotient) chart. |
| `…/P1IntrinsicEnergyAtlasCertificate.lean` | medium | Intrinsic energy-atlas certificate. |
| `…/P1OneDimensionalNormalMass.lean` | medium | One-dimensional normal mass. |

### D. P2 NSRS (Non-periodic Sheet / Root-cell Supplement)

| Path | Lines | Description |
| --- | --- | --- |
| `…/P2NSRSFrozenGramProjection.lean` | 1292 | Frozen-Gram projection for the NSRS chart. |
| `…/P2NSRSFixedLevelSlice.lean` | 1078 | Fixed-level slice of the NSRS chart. |
| `…/P2NSRSFrozenSliceKernel.lean` | 923 | Frozen-slice kernel (the rescaled posterior on the fixed slice). |
| `…/P2NSRSEuclideanInverseDifferential.lean` | 1001 | Euclidean inverse differential (change-of-variables Jacobian). |
| `…/P2NSRSPivotNormalScale.lean` | 905 | Pivot normal scale (the literal Gaussian width on the normal direction). |
| `…/P2NSRSEuclideanProductCoordinate.lean` | 617 | Euclidean product coordinate (chart representation). |
| `…/P2NSRSPositiveWitnessOwnership.lean` | 565 | Positive-witness ownership (every root cell owns a positive witness). |
| `…/P2NSRSNearLevelPhysicalAllocation.lean` | 458 | Near-level physical allocation. |
| `…/P2NSRSClosedGridTaylor.lean` | 449 | Closed-grid Taylor expansion. |
| `…/P2NSRSEuclideanLocalGaussianCOV.lean` | 448 | Euclidean local-Gaussian CoV. |
| `…/P2NSRSPeriodicSheetDerivative.lean` | 544 | Periodic-sheet derivative bound. |
| `…/P2NSRSFixedLevelHausdorffBounds.lean` | 521 | Fixed-level Hausdorff bounds. |
| `…/P2NSRSFixedNormalGram.lean` | 507 | Fixed normal-Gram. |
| `…/P2NSRSCanonicalCellCover.lean` | 388 | Canonical cell cover. |
| `…/P2NSRSNearLevelFrozenGramInterface.lean` | 365 | Near-level frozen-Gram interface. |
| `…/P2NSRSGaussianPriorCompatibility.lean` | 379 | Gaussian-prior compatibility on the NSRS chart. |
| `…/P2NSRSPeriodicP1Calibration.lean` | 379 | P1 calibration constants pulled back to the periodic NSRS chart. |
| `…/P2NSRSGlobalPhysicalCover.lean` | 368 | Global physical cover (union of root cells + sheet tube). |
| `…/P2NSRSPromotedComplementTail.lean` | 411 | Promoted complement tail. |
| `…/P2NSRSDerivedLocalGeometry.lean` | 415 | Derived local geometry (chart pulled back from the residual). |
| `…/P2NSRSEuclideanInverseRescaling.lean` | 415 | Euclidean inverse rescaling. |
| `…/P2NSRSEuclideanProductOwnership.lean` | medium | Euclidean product ownership (every point owns a positive chart neighbourhood). |
| `…/P2NSRSEuclideanProductShear.lean` | medium | Euclidean product shear (chart anisotropy bound). |
| `…/P2NSRSFibreSkeleton.lean` | medium | Fibre skeleton (the part of the fibre visible at every chart). |
| `…/P2NSRSFiniteSourceHeadRefinement.lean` | medium | Finite-source head refinement. |
| `…/P2AffineSheetGeometry.lean` | medium | Affine-sheet geometry (degenerates). |
| `…/P2InverseResidualChartCoV.lean` | medium | Inverse-residual chart CoV. |
| `…/P2NSRSActualAllocationGaussianBridge.lean` | medium | Actual-allocation Gaussian bridge. |
| `…/P2NSRSActualTubeAllocation.lean` | medium | Actual tube allocation. |
| `…/P2NSRSBaseJointVolume.lean` | medium | Base-joint volume bound. |
| `…/P2NSRSCanonicalCellDistortion.lean` | medium | Canonical cell distortion bound. |
| `…/P2NSRSCanonicalComplementSuppression.lean` | medium | Canonical complement suppression. |
| `…/P2NSRSCanonicalGridCOV.lean` | medium | Canonical grid CoV. |
| `…/P2NSRSCanonicalPhysicalRegion.lean` | medium | Canonical physical region. |
| `…/P2NSRSCleanStratumCompatibility.lean` | medium | Clean-stratum compatibility. |
| `…/P2NSRSCompactNormalDCT.lean` | medium | Compact-normal dominated-convergence theorem. |
| `…/P2NSRSCountableOwnershipCover.lean` | medium | Countable ownership cover. |
| `…/P2NSRSDerivedNormalScale.lean` | medium | Derived normal scale. |
| `…/P2NSRSEscapingWitnessC2Entry.lean` | medium | Escaping-witness C2 entry. |
| `…/P2NSRSEuclideanInverseCOV.lean` | medium | Euclidean inverse CoV. |
| `…/P2NSRSEuclideanInverseRegularity.lean` | medium | Euclidean inverse regularity. |
| `…/P2NSRSForwardResidualNormalCancellation.lean` | medium | Forward-residual normal cancellation. |
| `…/P2NSRSFrozenAdjointGram.lean` | medium | Frozen adjoint Gram. |
| `…/P2NSRSInverseBlockVolume.lean` | medium | Inverse-block volume bound. |
| `…/P2NSRSInverseProductOwnership.lean` | medium | Inverse product ownership. |
| `…/P2NSRSInverseVolumeFactorisation.lean` | medium | Inverse volume factorisation. |
| `…/P2NSRSIntrinsicGqBudget.lean` | medium | Intrinsic Gq budget (Gaussian quotient on the NSRS chart). |
| `…/P2NSRSIntrinsicGqBudgetHead.lean` | medium | Head of the intrinsic Gq budget. |
| `…/P2NSRSIntrinsicGqBudgetMass.lean` | medium | Mass part of the intrinsic Gq budget. |
| `…/P2NSRSIntrinsicGqBudgetTail.lean` | medium | Tail of the intrinsic Gq budget. |
| `…/P2NSRSLocalCOVCell.lean` | medium | Local CoV cell. |
| `…/P2NSRSLocalChart.lean` | medium | Local chart definition. |
| `…/P2NSRSMeasurableNormalFrame.lean` | medium | Measurable normal frame. |
| `…/P2NSRSNormalGaussianIntegrability.lean` | medium | Normal-Gaussian integrability. |
| `…/P2NSRSNormalGramBase.lean` | medium | Normal-Gram base case. |
| `…/P2NSRSNormalInverseVolume.lean` | medium | Normal inverse volume. |
| `…/P2NSRSOwnedLocalCOVCell.lean` | medium | Owned local CoV cell. |
| `…/P2NSRSPeriodicBudgetGeometry.lean` | medium | Periodic budget geometry. |
| `…/P2NSRSPeriodicBudgetReduction.lean` | medium | Periodic budget reduction. |
| `…/P2NSRSPeriodicCleanCompatibility.lean` | medium | Periodic clean compatibility. |
| `…/P2NSRSPeriodicExplicitNonescape.lean` | medium | Periodic explicit non-escape. |
| `…/P2NSRSPeriodicGaussianPacking.lean` | medium | Periodic Gaussian packing (companion to Lemma 5). |
| `…/P2NSRSPeriodicGenericPosteriorBridge.lean` | medium | Periodic generic posterior bridge. |
| `…/P2NSRSPeriodicNormalGram.lean` | medium | Periodic normal Gram. |
| `…/P2NSRSPeriodicRootEnvelope.lean` | medium | Periodic root envelope. |
| `…/P2NSRSPeriodicSheetEnvelope.lean` | medium | Periodic sheet envelope. |
| `…/P2NSRSPeriodicSheetHausdorffBudget.lean` | medium | Periodic sheet Hausdorff budget. |
| `…/P2NSRSPeriodicSheetParametrization.lean` | medium | Periodic sheet parametrization. |
| `…/P2NSRSPeriodicSheetPivotCramer.lean` | medium | Periodic sheet pivot Cramer bound. |
| `…/P2NSRSPeriodicSheetTaylor.lean` | medium | Periodic sheet Taylor expansion. |
| `…/P2NSRSPeriodicTaylorCertificate.lean` | medium | Periodic Taylor certificate. |
| `…/P2NSRSRealisedSharpness.lean` | medium | Realised sharpness of the NSRS chart. |
| `…/P2NSRSRescaledPosteriorKernel.lean` | medium | Rescaled posterior kernel. |
| `…/P2NSRSResidualCoordinateComparison.lean` | 612 | Residual-coordinate comparison. |
| `…/P2NSRSResidualNormalTangentAssembly.lean` | medium | Residual normal-tangent assembly. |
| `…/P2NSRSStratumOwnership.lean` | medium | Stratum ownership (every stratum owns a positive witness). |
| `…/P2NSRSWitnessAudit.lean` | medium | Witness audit (the bookkeeping lemma for the P2 NSRS proof package). |
| `…/P2NSRSWitnessC2Entry.lean` | medium | Witness C2 entry. |

### E. P2 / P3 profile, sheet, and root-cell layer

| Path | Lines | Description |
| --- | --- | --- |
| `…/P2PositiveProductNormalChart.lean` | 430 | Positive-product normal chart (the literal `e^{rho^2/2}/a` coefficient comes from this geometry). |
| `…/P2PeriodicProfileSheetLaw.lean` | 614 | Periodic-profile sheet law. |
| `…/P2ProfileFullEvidence.lean` | medium | Full evidence (sheet + cells + complement). |
| `…/P2ProfileFullObservable.lean` | medium | Full observable (test function φ applied to the full posterior). |
| `…/P2ProfileFullPhysicalAssembly.lean` | medium | Full physical assembly. |
| `…/P2ProfileGaussianDensity.lean` | medium | Gaussian density on the profile. |
| `…/P2ProfileIsolatedChangeOfVariables.lean` | medium | Isolated cell CoV. |
| `…/P2ProfileIsolatedRescaling.lean` | medium | Isolated cell rescaling. |
| `…/P2ProfileIsolatedTubeMass.lean` | medium | Isolated tube mass (literal `C_g e^{-z^2/4} eps^2` bound). |
| `…/P2ProfileLiteralComplementGap.lean` | medium | Literal complement gap (the `e_rho > 0` min of `rho^4` and `(1-rho)^2 eta^2`). |
| `…/P2ProfilePosteriorMeasure.lean` | medium | Posterior measure on the profile. |
| `…/P2ProfileRootCountability.lean` | medium | Root countability (`Z_g` is at most countable). |
| `…/P2ProfileRootPosteriorRemainder.lean` | medium | Root posterior remainder. |
| `…/P2ProfileSharedAllocation.lean` | medium | Shared allocation across root cells. |
| `…/P2ProfileSharedRemainders.lean` | medium | Shared remainders. |
| `…/P2ProfileSheetBoundary.lean` | medium | Sheet boundary (the part of `∂S` relevant to the sheet tube). |
| `…/P2ProfileSheetChangeOfVariables.lean` | medium | Sheet CoV. |
| `…/P2ProfileSheetDerivative.lean` | medium | Sheet derivative bound. |
| `…/P2ProfileSheetEvidence.lean` | medium | Sheet evidence `A_g` definition and positivity (paper's `A_g` from line 161). |
| `…/P2ProfileSheetObservable.lean` | medium | Sheet observable (sheet tube integral of `φ`). |
| `…/P2ProfileComplementRemainder.lean` | medium | Complement remainder (paper's Lemma 4 exponential tail). |
| `…/P2NonperiodicSheetGeometry.lean` | medium | Nonperiodic sheet geometry. |
| `…/P2NormalResidualGeometry.lean` | medium | Normal residual geometry. |
| `…/P2PeriodicCleanFibreRescaling.lean` | medium | Periodic clean-fibre rescaling. |
| `…/P2PeriodicPosteriorNormalization.lean` | medium | Periodic posterior normalization. |
| `…/P2ProfileSheetRescaling.lean` | medium | Sheet rescaling (used in Lemma 2). |
| `…/P2ResidualNonescape.lean` | medium | Residual non-escape. |
| `…/P2NearLevelGapCounterexample.lean` | medium | Near-level-gap counterexample (companion to `…/P1EscapedNearLevelObstruction`). |
| `…/P2StrictDerivativeMetricCell.lean` | medium | Strict-derivative metric cell. |
| `…/P2StrictPhysicalIncidence.lean` | medium | Strict physical incidence. |
| `…/P2StrictProfileTubeGeometry.lean` | medium | Strict-profile tube geometry. |
| `…/P2UniformlySeparatedSheetRescaling.lean` | medium | Uniformly-separated sheet rescaling. |
| `…/P3PeriodicProfileSharpness.lean` | medium | Periodic profile sharpness (companion to `…/P2NSRSRealisedSharpness`). |

### F. Radial-twist local geometry, midpoint, and OU/OU-marginal

The biggest single cluster: 95+ files on the radial-twist model.

| Path | Lines | Description |
| --- | --- | --- |
| `…/RadialTwistMidpointInfiniteRadialFibers.lean` | 2064 | Midpoint infinite radial fibres (largest single file). |
| `…/RadialTwistPosteriorKernelObservationDerivative.lean` | 1920 | Posterior-kernel observation derivative. |
| `…/RadialTwistMidpointRegularPhaseSafeNeighborhood.lean` | 1693 | Midpoint regular-phase safe neighbourhood. |
| `…/RadialTwistMidpointAdaptiveTubeSeries.lean` | 1643 | Midpoint adaptive tube series. |
| `…/RadialTwistTailVelocity.lean` | 1258 | Tail velocity asymptotics. |
| `…/RadialTwistOUOffBalanceConditionalMoment.lean` | 1026 | OU off-balance conditional moment. |
| `…/RadialTwistPosteriorMaximalContinuation.lean` | 934 | Posterior maximal continuation. |
| `…/RadialTwistMidpointLowEnergyWideningCover.lean` | 808 | Midpoint low-energy widening cover. |
| `…/RadialTwistMidpointRegularLocalNumerator.lean` | 738 | Midpoint regular local numerator. |
| `…/RadialTwistMidpointRegularLocalLaplace.lean` | 651 | Midpoint regular local Laplace. |
| `…/RadialTwistMidpointOneCirclePrelimitTail.lean` | 644 | Midpoint one-circle prelimit tail. |
| `…/RadialTwistMidpointOneCircleGaussianScaling.lean` | 578 | Midpoint one-circle Gaussian scaling. |
| `…/RadialTwistMidpointRegularLocalFamily.lean` | 589 | Midpoint regular local family. |
| `…/RadialTwistMidpointTargetEnergyBandTransport.lean` | 535 | Midpoint target energy-band transport. |
| `…/RadialTwistMidpointCausticTubePolarBridge.lean` | 525 | Midpoint caustic tube polar bridge. |
| `…/RadialTwistBalancedPhaseGeometry.lean` | 512 | Balanced-phase geometry. |
| `…/RadialTwistCoreAnnulusNumerator.lean` | 564 | Core annulus numerator. |
| `…/RadialTwistPreterminalMidpointScalarComponents.lean` | 545 | Preterminal midpoint scalar components. |
| `…/RadialTwistCoreAnnulusDenominator.lean` | 477 | Core annulus denominator. |
| `…/RadialTwistMidpointCircleSeriesTannery.lean` | 445 | Midpoint circle series Tannery. |
| `…/RadialTwistBalancedStripDenominator.lean` | 431 | Balanced strip denominator. |
| `…/RadialTwistMidpointRegularPhasePartition.lean` | 424 | Midpoint regular-phase partition. |
| `…/RadialTwistBalancedBadTubeMass.lean` | 407 | Balanced bad tube mass. |
| `…/RadialTwistLocalCoreNumerator.lean` | 395 | Local core numerator. |
| `…/RadialTwistCoreOverlap.lean` | 389 | Core overlap (mass between adjacent cores). |
| `…/RadialTwistCausticLaw.lean` | 376 | Caustic law. |
| `…/RadialTwistTerminalOutsideTightness.lean` | 367 | Terminal outside tightness. |
| `…/RadialTwistNearBalancePreimage.lean` | 381 | Near-balance preimage. |
| `…/RadialTwistBalancedStripRadialNumerator.lean` | 375 | Balanced strip radial numerator. |
| `…/RadialTwistGlobalTerminalSeparation.lean` | 375 | Global terminal separation. |
| `…/RadialTwistMidpointTargetCompactGap.lean` | 376 | Midpoint target compact gap. |
| `…/RadialTwistOUContractedLocalDenominator.lean` | 598 | OU contracted local denominator. |
| `…/RadialTwistBalancedAllIntegerBadTail.lean` | medium | Balanced all-integer bad tail. |
| `…/RadialTwistBalancedAngularRetention.lean` | medium | Balanced angular retention. |
| `…/RadialTwistBalancedBadTubeQuotient.lean` | medium | Balanced bad-tube quotient. |
| `…/RadialTwistBalancedFinalQuotient.lean` | medium | Balanced final quotient. |
| `…/RadialTwistBalancedGoodPhaseNumerator.lean` | medium | Balanced good-phase numerator. |
| `…/RadialTwistBalancedLocalDenominator.lean` | medium | Balanced local denominator. |
| `…/RadialTwistBalancedPhaseCovering.lean` | medium | Balanced phase covering. |
| `…/RadialTwistBalancedRadialPreimage.lean` | medium | Balanced radial preimage. |
| `…/RadialTwistBalancedRemoteTubeCutoff.lean` | medium | Balanced remote-tube cutoff. |
| `…/RadialTwistBalancedStripLinearMoment.lean` | medium | Balanced strip linear moment. |
| `…/RadialTwistBalancedStripParameterSelection.lean` | medium | Balanced strip parameter selection. |
| `…/RadialTwistBalancedStripQuotient.lean` | medium | Balanced strip quotient. |
| `…/RadialTwistBalancedStripRadialDenominator.lean` | medium | Balanced strip radial denominator. |
| `…/RadialTwistBoundaryLayerKernelProfile.lean` | medium | Boundary-layer kernel profile. |
| `…/RadialTwistCM4CoverObstruction.lean` | medium | CM4 cover obstruction. |
| `…/RadialTwistCM4RelativeRegimeCover.lean` | medium | CM4 relative-regime cover. |
| `…/RadialTwistCM4UniformConditionalMoment.lean` | medium | CM4 uniform conditional moment. |
| `…/RadialTwistCausticRadiusSummability.lean` | medium | Caustic radius summability. |
| `…/RadialTwistCausticTubeDisjointness.lean` | medium | Caustic tube disjointness. |
| `…/RadialTwistCharacteristicEndpointPromotion.lean` | medium | Characteristic endpoint promotion. |
| `…/RadialTwistContractedReferenceCurve.lean` | medium | Contracted reference curve. |
| `…/RadialTwistCoreAnnulusSchedule.lean` | medium | Core annulus schedule. |
| `…/RadialTwistCoreBounds.lean` | medium | Core bounds. |
| `…/RadialTwistCoreCenteredDecomposition.lean` | medium | Core centered decomposition. |
| `…/RadialTwistCoreCenteredLimit.lean` | medium | Core centered limit. |
| `…/RadialTwistCoreInjectivity.lean` | medium | Core injectivity. |
| `…/RadialTwistCoreInteriorMargin.lean` | medium | Core interior margin. |
| `…/RadialTwistCoreInverse.lean` | medium | Core inverse. |
| `…/RadialTwistCoreJacobian.lean` | medium | Core Jacobian. |
| `…/RadialTwistCorePosteriorGate.lean` | medium | Core posterior gate. |
| `…/RadialTwistCorePushforward.lean` | medium | Core pushforward. |
| `…/RadialTwistCountableRegularBranchQuotient.lean` | medium | Countable regular-branch quotient (companion to `CountableStratified…`). |
| `…/RadialTwistDissipation.lean` | medium | Dissipation bound. |
| `…/RadialTwistFixedWindowCenteredLimit.lean` | medium | Fixed-window centered limit. |
| `…/RadialTwistFixedWindowNormalizedCenteredLimit.lean` | medium | Fixed-window normalized centered limit. |
| `…/RadialTwistFixedWindowPosteriorLimit.lean` | medium | Fixed-window posterior limit. |
| `…/RadialTwistFiniteRegularBranchQuotient.lean` | medium | Finite regular-branch quotient. |
| `…/RadialTwistFullFixedCentreLimit.lean` | medium | Full fixed-centre limit. |
| `…/RadialTwistFullPushforwardDecomposition.lean` | medium | Full pushforward decomposition. |
| `…/RadialTwistGeneratorSelectionBoundary.lean` | medium | Generator selection boundary. |
| `…/RadialTwistGlobalOutsideCenteredDefect.lean` | medium | Global outside centered defect. |
| `…/RadialTwistGlobalOutsideDenominator.lean` | medium | Global outside denominator. |
| `…/RadialTwistGlobalOutsideNumerator.lean` | medium | Global outside numerator. |
| `…/RadialTwistLinearizedOddCancellation.lean` | medium | Linearized odd cancellation. |
| `…/RadialTwistLocalCorePosterior.lean` | medium | Local core posterior. |
| `…/RadialTwistLocalPosteriorProfile.lean` | medium | Local posterior profile. |
| `…/RadialTwistLocalPosteriorRescaling.lean` | medium | Local posterior rescaling. |
| `…/RadialTwistMidpointCausticCircleNormalRemainder.lean` | medium | Midpoint caustic circle normal remainder. |
| `…/RadialTwistMidpointCausticComplementExhaustion.lean` | medium | Midpoint caustic complement exhaustion. |
| `…/RadialTwistMidpointCausticLinearization.lean` | medium | Midpoint caustic linearization. |
| `…/RadialTwistMidpointCausticRadialRemainder.lean` | medium | Midpoint caustic radial remainder. |
| `…/RadialTwistMidpointCausticTailSchedule.lean` | medium | Midpoint caustic tail schedule. |
| `…/RadialTwistMidpointCausticTubeCoordinates.lean` | medium | Midpoint caustic tube coordinates. |
| `…/RadialTwistMidpointCausticTubeDecomposition.lean` | medium | Midpoint caustic tube decomposition. |
| `…/RadialTwistMidpointCausticVelocityAssembly.lean` | medium | Midpoint caustic velocity assembly. |
| `…/RadialTwistMidpointEnergyComplementGap.lean` | medium | Midpoint energy complement gap. |
| `…/RadialTwistMidpointExpandingCompactGapAudit.lean` | medium | Midpoint expanding compact gap audit. |
| `…/RadialTwistMidpointNoncausticCompactGap.lean` | medium | Midpoint non-caustic compact gap. |
| `…/RadialTwistMidpointNoncausticCompactIntegral.lean` | medium | Midpoint non-caustic compact integral. |
| `…/RadialTwistMidpointOddNumeratorCancellation.lean` | medium | Midpoint odd numerator cancellation. |
| `…/RadialTwistMidpointOneCircleAngularLift.lean` | medium | Midpoint one-circle angular lift. |
| `…/RadialTwistMidpointOneCircleFullNormal.lean` | medium | Midpoint one-circle full normal. |
| `…/RadialTwistMidpointPositiveNoiseRootTannery.lean` | medium | Midpoint positive-noise root Tannery. |
| `…/RadialTwistMidpointPosteriorVelocity.lean` | medium | Midpoint posterior velocity. |
| `…/RadialTwistMidpointRegularLocalChart.lean` | medium | Midpoint regular local chart. |
| `…/RadialTwistMidpointSmallNoiseCellIntegration.lean` | medium | Midpoint small-noise cell integration. |
| `…/RadialTwistMidpointSmallNoisePhaseBudget.lean` | medium | Midpoint small-noise phase budget. |
| `…/RadialTwistMidpointSmallNoiseScalarMajorant.lean` | medium | Midpoint small-noise scalar majorant. |
| `…/RadialTwistNearBalanceDenominator.lean` | medium | Near-balance denominator. |
| `…/RadialTwistNearBalanceLinearMoment.lean` | medium | Near-balance linear moment. |
| `…/RadialTwistNearBalanceParameterSelection.lean` | medium | Near-balance parameter selection. |
| `…/RadialTwistNearBalanceQuotient.lean` | medium | Near-balance quotient. |
| `…/RadialTwistNearBalanceRadialDenominator.lean` | medium | Near-balance radial denominator. |
| `…/RadialTwistNearBalanceRadialNumerator.lean` | medium | Near-balance radial numerator. |
| `…/RadialTwistOUContractedBalanceTime.lean` | medium | OU contracted balance time. |
| `…/RadialTwistOUContractedCoercivity.lean` | medium | OU contracted coercivity. |
| `…/RadialTwistOUContractedInjectivity.lean` | medium | OU contracted injectivity. |
| `…/RadialTwistOUContractedMap.lean` | medium | OU contracted map. |
| `…/RadialTwistOUContractedRadialSurjectivity.lean` | medium | OU contracted radial surjectivity. |
| `…/RadialTwistOUContractedSurjectivity.lean` | medium | OU contracted surjectivity. |
| `…/RadialTwistOUCoreBoundaryLayer.lean` | medium | OU core boundary layer. |
| `…/RadialTwistPositiveNoiseNumerator.lean` | medium | Positive-noise numerator. |
| `…/RadialTwistPositiveNoisePosterior.lean` | medium | Positive-noise posterior. |
| `…/RadialTwistPositiveNoiseVelocity.lean` | medium | Positive-noise velocity. |
| `…/RadialTwistPosteriorCharacteristicGronwall.lean` | medium | Posterior characteristic Grönwall. |
| `…/RadialTwistPosteriorCharacteristicUniqueness.lean` | medium | Posterior characteristic uniqueness. |
| `…/RadialTwistPosteriorDenominatorCompactCylinder.lean` | medium | Posterior denominator compact cylinder. |
| `…/RadialTwistPosteriorDenominatorParameterContinuity.lean` | medium | Posterior denominator parameter continuity. |
| `…/RadialTwistPosteriorDenominatorSpatialModulus.lean` | medium | Posterior denominator spatial modulus. |
| `…/RadialTwistPosteriorFixedRefreshDerivativeLocality.lean` | medium | Posterior fixed-refresh derivative locality. |
| `…/RadialTwistPosteriorFixedRefreshDerivativeTail.lean` | medium | Posterior fixed-refresh derivative tail. |
| `…/RadialTwistPosteriorFixedRefreshLocalLipschitz.lean` | medium | Posterior fixed-refresh local Lipschitz. |
| `…/RadialTwistPosteriorLocalCharacteristic.lean` | medium | Posterior local characteristic. |
| `…/RadialTwistPosteriorLocalRestartCharacteristic.lean` | medium | Posterior local-restart characteristic. |
| `…/RadialTwistPosteriorNumeratorCompactCylinder.lean` | medium | Posterior numerator compact cylinder. |
| `…/RadialTwistPosteriorNumeratorParameterContinuity.lean` | medium | Posterior numerator parameter continuity. |
| `…/RadialTwistPosteriorNumeratorSpatialModulus.lean` | medium | Posterior numerator spatial modulus. |
| `…/RadialTwistPosteriorObservationJacobian.lean` | medium | Posterior observation Jacobian. |
| `…/RadialTwistPosteriorPreterminalCharacteristic.lean` | medium | Posterior preterminal characteristic. |
| `…/RadialTwistPosteriorSpatialModulus.lean` | medium | Posterior spatial modulus. |
| `…/RadialTwistPosteriorVelocityCompactCylinder.lean` | medium | Posterior velocity compact cylinder. |
| `…/RadialTwistPosteriorVelocityGrowth.lean` | medium | Posterior velocity growth. |
| `…/RadialTwistPosteriorVelocityParameterContinuity.lean` | medium | Posterior velocity parameter continuity. |
| `…/RadialTwistPreterminalFullBranchQuotientGate.lean` | medium | Preterminal full-branch quotient gate. |
| `…/RadialTwistPreterminalMidpointFixedEvidence.lean` | medium | Preterminal midpoint fixed evidence. |
| `…/RadialTwistPreterminalMidpointTubeBridge.lean` | medium | Preterminal midpoint tube bridge. |
| `…/RadialTwistPreterminalPhasePartition.lean` | medium | Preterminal phase partition. |
| `…/RadialTwistPreterminalPhysicalAllocation.lean` | medium | Preterminal physical allocation. |
| `…/RadialTwistPreterminalPhysicalComponents.lean` | medium | Preterminal physical components. |
| `…/RadialTwistPreterminalPhysicalSymmetry.lean` | medium | Preterminal physical symmetry. |
| `…/RadialTwistPreterminalRefreshLimitAtom.lean` | medium | Preterminal refresh-limit atom. |
| `…/RadialTwistPreterminalSourceTailKernel.lean` | medium | Preterminal source-tail kernel. |
| `…/RadialTwistPreterminalThreeWayQuotient.lean` | medium | Preterminal three-way quotient. |
| `…/RadialTwistPreterminalThreeWayQuotientLimit.lean` | medium | Preterminal three-way quotient limit. |
| `…/RadialTwistPreterminalUniformKernelBridge.lean` | medium | Preterminal uniform kernel bridge. |
| `…/RadialTwistPreterminalUniformSourceTail.lean` | medium | Preterminal uniform source tail. |
| `…/RadialTwistRLFFixedNoiseVelocity.lean` | medium | RLF fixed-noise velocity. |
| `…/RadialTwistRLFHypotheses.lean` | medium | RLF hypotheses. |
| `…/RadialTwistRLFTimeIntegrability.lean` | medium | RLF time integrability. |
| `…/RadialTwistTerminalAdvectedEnvelope.lean` | medium | Terminal advected envelope. |
| `…/RadialTwistTerminalTubeTracking.lean` | medium | Terminal tube tracking. |

### G. Gaussian / Hermite / Planar / OU machinery

Foundational Gaussian and Hermite modules.

| Path | Lines | Description |
| --- | --- | --- |
| `…/GaussianAngle.lean` | 635 | Gaussian-angle machinery. |
| `…/GaussianRadialTwistFlow.lean` | 705 | Gaussian radial-twist flow. |
| `…/GaussianRadialTwistDifferential.lean` | medium | Radial-twist differential. |
| `…/GaussianRadialTwist.lean` | medium | Radial-twist definition and basic identity. |
| `…/GaussianRadialTwistGlobalLpFlow.lean` | medium | Global Lp flow of the radial twist. |
| `…/GaussianRadialTwistProbability.lean` | medium | Probability-law consequences of the radial twist. |
| `…/GaussianRadialTwistWeakContinuity.lean` | medium | Weak continuity of the radial twist. |
| `…/GaussianFirstHermiteHodge.lean` | medium | First Hermite-Hodge spectrum. |
| `…/GaussianFirstMomentAnnulus.lean` | medium | First moment annulus. |
| `…/GaussianLinearSkewMultiplier.lean` | medium | Linear-skew multiplier. |
| `…/GaussianMomentClosure.lean` | medium | Moment closure. |
| `…/GaussianPlanarMatrixODE.lean` | medium | Planar matrix ODE. |
| `…/GaussianSummableObstruction.lean` | medium | Summable obstruction (when a Gaussian family fails summability). |
| `…/GaussianViscosityGenerator.lean` | medium | Viscosity generator of the Gaussian radial twist. |
| `…/HermiteBoundaryLayerAsymptotic.lean` | medium | Hermite boundary-layer asymptotic. |
| `…/HermiteCrossoverKernel.lean` | 405 | Hermite crossover kernel. |
| `…/HermiteFiniteNoiseBoundaryLayer.lean` | medium | Hermite finite-noise boundary layer. |
| `…/HermiteFiniteNoiseOrdering.lean` | medium | Hermite finite-noise ordering. |
| `…/HermiteHodgeSpectrum.lean` | medium | Hermite-Hodge spectrum (general). |
| `…/PlanarAdditiveGaussianKernelNormalization.lean` | medium | Planar additive Gaussian kernel normalization. |
| `…/PlanarEnergyNormBridge.lean` | medium | Planar energy-norm bridge. |
| `…/PlanarGaussianAffineKernelDisintegration.lean` | medium | Planar affine-kernel disintegration. |
| `…/PlanarMehlerKernel.lean` | medium | Planar Mehler kernel. |
| `…/OUContractionFirstOrder.lean` | medium | OU contraction, first order. |
| `…/OUPosteriorBoundaryLayer.lean` | medium | OU posterior boundary layer. |
| `…/BrenierStationarity.lean` | medium | Brenier stationarity (monotone-transport fixed point). |
| `…/QuarticBrenierStationarity.lean` | medium | Quartic Brenier stationarity. |
| `…/QuarticWeightedTail.lean` | medium | Quartic weighted tail. |
| `…/WeightedHodgeStationarity.lean` | medium | Weighted Hodge stationarity. |
| `…/LawBasedOUEnergy.lean` | medium | Law-based OU energy. |
| `…/CalibratedPosteriorAction.lean` | medium | Calibrated posterior action. |
| `…/CausticGaussianTail.lean` | medium | Caustic Gaussian tail. |
| `…/CleanStratumGaussianLocalization.lean` | 389 | Clean-stratum Gaussian localization. |
| `…/CompactPositiveQuotientGate.lean` | medium | Compact positive quotient gate. |
| `…/CompactlySupportedC1Bridge.lean` | medium | Compactly supported C1 bridge. |
| `…/ConditionalExpectationTailContraction.lean` | medium | Conditional-expectation tail contraction. |
| `…/ConditionalVelocityContinuityEquation.lean` | 426 | Conditional-velocity continuity equation. |
| `…/ConditionalVelocityIdentification.lean` | medium | Conditional-velocity identification. |
| `…/EndpointODEStability.lean` | medium | Endpoint ODE stability. |
| `…/EndpointUniformRemainder.lean` | medium | Endpoint uniform remainder. |
| `…/EpsilonRadiusGluing.lean` | medium | Epsilon radius gluing. |
| `…/FiniteActionPathEndpoint.lean` | medium | Finite-action path endpoint. |
| `…/FiniteObstructions.lean` | medium | Finite obstructions. |
| `…/JointConditionalVelocityRepresentative.lean` | medium | Joint conditional-velocity representative. |
| `…/MultibranchLikelihoodAmplification.lean` | medium | Multibranch likelihood amplification. |
| `…/NonlinearConditionalVelocityPairing.lean` | medium | Nonlinear conditional-velocity pairing. |
| `…/PolynomialFlowCompletenessObstruction.lean` | medium | Polynomial-flow completeness obstruction. |
| `…/PosteriorVelocityBayesCalibration.lean` | medium | Posterior-velocity Bayes calibration. |
| `…/PreterminalBorelWeakContinuity.lean` | medium | Preterminal Borel weak continuity. |
| `…/PreterminalObservationLaw.lean` | medium | Preterminal observation law. |
| `…/PreterminalWeakTimeIntegrability.lean` | medium | Preterminal weak-time integrability. |
| `…/RegularFlowCesaroTangent.lean` | medium | Regular-flow Cesàro tangent. |
| `…/RegularFlowTangentDomain.lean` | medium | Regular-flow tangent domain. |
| `…/ScalarObservationDisintegration.lean` | 445 | Scalar observation disintegration. |
| `…/SeparableTimeSpaceCompactC1Bridge.lean` | medium | Separable time-space compact C1 bridge. |
| `…/SpectralViscosityBudget.lean` | medium | Spectral viscosity budget. |
| `…/TerminalTwoScaleSchedule.lean` | medium | Terminal two-scale schedule. |
| `…/TranslatedDilatedGaussianMass.lean` | medium | Translated-dilated Gaussian mass. |
| `…/TranslatedDilatedIntegral.lean` | medium | Translated-dilated integral. |
| `…/TwoParameterLimitOrderObstruction.lean` | medium | Two-parameter limit-order obstruction. |
| `…/VariableGaussianAnnulusSchedule.lean` | medium | Variable Gaussian annulus schedule. |

### H. Manuscript / misc

The repo contains a `Research/NoiseSelectedRectification/manuscript/` tree with
LaTeX source (`en/main.tex`) and submission materials (cover letter template,
README). These are non-`.lean` artifacts and are not enumerated here.

---

## Summary

The repo's `.lean` surface splits naturally into five responsibilities:

1. **FlowA / FlowoE architecture contract** (`FlowA/` + `FlowAArchitectureProofs.lean`,
   2,659 lines) — architecture feasibility only; no empirical metric claims.
2. **Noise-selected rectification theorem** (`Research/NoiseSelectedRectification/`,
   461 files, ~133,000 lines) — the bulk of the formalization, covering the
   countable-stratum selection theorem, P1 atlas & actual-posterior assembly,
   P2 NSRS, P2 profile/sheet/root-cell layer, the radial-twist midpoint and
   OU machinery, and Gaussian / Hermite / Brenier building blocks.
3. **Commutator-safe channel freezing** (`Research/CommutatorSafeChannelFreezing/`,
   6 files) — bracket calibration and counterexamples for the
   inferenceChannelFreeze claim.
4. **FlowoE expert aggregation** (`Research/FlowOEExpertAggregation/`, 3 files)
   — SBVC, finite-horizon predictive entropy, and minimal-phase-memory
   routing.
5. **Stratified chemical transport** (`Research/StratifiedChemicalTransport/`,
   8 files) — formal layer supporting the FlowA chemical-rescue mechanism.

The cited line counts were derived from `find … -exec wc -l {} \;` on
2026-08-28.