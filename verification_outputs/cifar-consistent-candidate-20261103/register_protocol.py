from pathlib import Path
from datetime import datetime,UTC
import json,hashlib,subprocess
r=Path('/home/hugo/codes/flowa-multistep-reinference');p=r/'verification_outputs/cifar-consistent-candidate-20261103';p.mkdir(exist_ok=False)
parent=json.loads((r/'verification_outputs/cifar-study-20261103/PROTOCOL.json').read_text())
paths=['tools/cifar_consistent_candidate_20261103.py','tools/cifar_matched_frontier_20261103.py','tools/cifar_study_metrics_20261103.py']
def sha(f):return hashlib.sha256((r/f).read_bytes()).hexdigest()
s={'registered_utc':datetime.now(UTC).isoformat(),'kind':'local prospective configuration-and-generation-seed holdout lock; not public registry',
'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'source_sha256':{x:sha(x) for x in paths},
'motivation':'A separate hypothesis based on path/coupling analysis and the completed MNIST component study. Some seed42 first-study cells and pilot were already observed. The new configuration and seeds101/102/103 have never been run. This is not an independent model-family or dataset confirmation and not a seed topup for old full/simple comparisons.',
'hypothesis':'A two-round, time-consistent, path-length-proportional, centroid-free candidate may improve high-budget KID relative to Euler and RF-adapted original Restart; ideal target preservation alone is not an improvement guarantee.',
'new_configuration':'R2, beta_total=.3, memory=.7, first pass official RF Euler; one boundary x=.7*endpoint+.3*fresh Gaussian; second actual model time[.7,1], exact dt=.3/S2; no epsilon warp in second segment; no centroid shift or state clipping.',
'budget_allocation':{'99':[76,23],'199':[153,46]},'operator_novelty':'Uses existing proportional-allocation capability; not claimed as a newly invented re-noising operator.',
'arms':['baseline_euler','consistent_two_round','ve_restart'],'seeds':[101,102,103],'cost_grid':[99,199],'n_per_arm_seed_cost':1000,'canonical_jobs':6,
'controls':'Exact frozen first-study baseline_euler and ve_restart code, same model and shared initial prior under new seeds; never pool with seeds42/43/44 for significance.',
'primary_metric':'unscaled full10k-reference polynomial KID U-statistic; these3 arms have no global centroid operation. Three whole-generation seeds are inferential units.',
'primary_seed_statistic':'normalized log-cost area over exactly2 costs99/199, equivalent to their arithmetic mean; local high-budget comparison, not a complete frontier',
'primary_contrasts':[['consistent_two_round','baseline_euler'],['consistent_two_round','ve_restart']],
'primary_inference':'paired seed t df2, two-sided, Holm across exactly2 new-configuration contrasts; nominal95% CI not simultaneous; improvement requires Holm p<.05 and CI upper<-.001. This is not research-wide multiplicity control across all study designs.',
'secondary':'TF-port FID, clipping and sampling walltime. No additional significant-best-rung selection. No FID-bias subtraction.',
'activation':'Resource-only: after all12 first-study jobs finish successfully, available total7200 seconds minus first-study conservative accounting including prior360, profiles120 and Euler parity60 minus60 reserve must permit at least1800 seconds. Allocate min(2000,available). Otherwise DEFERRED before any holdout job. Do not activate based on quality scores.',
'per_cell_wall_cap_s':600,'execution_order':'seed101/102/103, each C99 then199; fixed arm order; all six cells or report incomplete',
'weights_path':parent['weights_path'],'weights_sha256':parent['weights_sha256'],'reference_path':parent['reference_path'],'reference_sha256':parent['reference_sha256'],'reference_statistics':parent['reference_statistics'],'reference_statistics_sha256':parent['reference_statistics_sha256'],'restart_source_path':parent['restart_source_path'],'restart_source_sha256':parent['restart_source_sha256'],
'physical_gpu':1,'environment':'.venvs/flowmol3_venv','dtype':'same fp32 Euler/model, original VE fp64-state policy; matmulTF32 false,cudnnTF32 true',
'prior_policy':'same numpy PCG64 Gaussian initial policy and SeedSequence([seed,1,0]) fresh noise, new held-out generation seeds only',
'visual_selection':'first32 saved perarm; if shown use first8 seed101 C199 with same display transform, no success selection',
'not_claimed':['full frontier WIN','new model family','independent training seeds','universal optimality','operator novelty','CAS1 acceptance guarantee']}
(p/'PROTOCOL.json').write_text(json.dumps(s,indent=2)+'\n');print(s['registered_utc'])
