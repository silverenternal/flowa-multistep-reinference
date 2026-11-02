from pathlib import Path
import subprocess,json,os,time,hashlib
from datetime import datetime,UTC
r=Path('/home/hugo/codes/flowa-multistep-reinference');os.chdir(r)
p=r/'verification_outputs/cifar-study-20261103';protocol=json.loads((p/'PROTOCOL.json').read_text())
ledger=json.loads((p/'RUN_LEDGER.json').read_text());assert len(ledger['jobs'])==1 and ledger['jobs'][0]['n']==32 and ledger['jobs'][0]['exit_code']==0
profile1=json.loads((p/'BRIDGE_PROFILE.json').read_text());profile2=json.loads((p/'SAMPLER_PROFILE.json').read_text())
# Cold-start timings cannot be multiplied by every canonical minibatch. This is a runtime-only correction.
warm=max(row['wall_s'] for row in profile1['rows'])
warm=max(warm,next(row['wall_s'] for row in profile2['rows'] if row['noise_implementation']=='numpy_copy_repeat'))
assert warm<.65, warm
projection=5*.65*(1000/32)*sum(protocol['cost_grid'])/25*3+12*60+ledger['used_study_s']
amend={'recorded_utc':datetime.now(UTC).isoformat(),'before_any_canonical_job':True,'initial_runtime_guard':'FAILED; preserved','reason':'Initial single-batch pilot extrapolated cold-start initialization into every minibatch. Separate runtime-only warm model/bridge/original-sampler profiles measure <=.65s per25 calls, with no metric or model-selection use.',
       'observed_max_warm25_call_s':warm,'conservative_per_arm_batch25_call_s':.65,'per_canonical_job_cold_scoring_IO_reserve_s':60,'projected_study_s':projection,'locked_study_cap_s':6000,
       'profiling_extra_budget_accounted_s':120,'user_total_cap_s':7200,'pass':projection<5700,
       'scientific_protocol_unchanged':True,'source_driver_unchanged':True,'no_change_to_seeds_N_arms_noise_solver_metrics_or_hypotheses':True,'protocol_sha256':hashlib.sha256((p/'PROTOCOL.json').read_bytes()).hexdigest()}
(p/'RUNTIME_AMENDMENT.json').write_text(json.dumps(amend,indent=2)+'\n');assert amend['pass']
ledger['profiling_extra_conservatively_accounted_s']=120
ledger['runtime_amendment_sha256']=hashlib.sha256((p/'RUNTIME_AMENDMENT.json').read_bytes()).hexdigest()
e=os.environ.copy();e.update(OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4',PYTHONPATH=str(r))
for seed in protocol['seeds']:
 for cost in protocol['cost_grid']:
  used=ledger['used_study_s'];assert used<6000
  out=p/f's{seed}_c{cost}';assert not out.exists()
  cmd=[str(r/'.venvs/flowmol3_venv/bin/python'),'tools/cifar_matched_frontier_20261103.py','--protocol',str(p/'PROTOCOL.json'),'--out',str(out),'--seed',str(seed),'--cost',str(cost),'--n','1000','--device','cuda:1']
  start=time.monotonic();registered=datetime.now(UTC).isoformat()
  with (p/(out.name+'.log')).open('w') as log:
   try:z=subprocess.run(cmd,env=e,stdout=log,stderr=subprocess.STDOUT,timeout=min(1200,6000-used));code=z.returncode
   except subprocess.TimeoutExpired:code=124
  elapsed=time.monotonic()-start;ledger['used_study_s']+=elapsed
  ledger['jobs'].append({'registered_utc':registered,'n':1000,'seed':seed,'cost':cost,'argv':cmd,'outer_wall_s':elapsed,'exit_code':code})
  (p/'RUN_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print(out.name,code,elapsed,'cumulative',ledger['used_study_s'],flush=True)
  if code:raise SystemExit(code)
ledger['complete']=True;ledger['conservatively_rounded_total_with_prior_and_profiles_s']=480+int(ledger['used_study_s']+1)
(p/'RUN_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print('ALL_COMPLETE',ledger['used_study_s'],flush=True)
