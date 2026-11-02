from pathlib import Path
from datetime import datetime,UTC
import os,subprocess,json,time
r=Path('/home/hugo/codes/flowa-multistep-reinference');os.chdir(r)
parent=r/'verification_outputs/cifar-study-20261103';root=r/'verification_outputs/cifar-consistent-candidate-20261103'
protocol=json.loads((root/'PROTOCOL.json').read_text());e=os.environ.copy();e.update(OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4',PYTHONPATH=str(r))
started_wait=time.monotonic()
while True:
 state=json.loads((parent/'RUN_LEDGER.json').read_text())
 if state.get('complete'):break
 if any(x['exit_code'] for x in state['jobs']):raise RuntimeError('first study failed; no holdout activation')
 if time.monotonic()-started_wait>6000:raise RuntimeError('parent wait timed out')
 time.sleep(15)
extra=json.loads((parent/'ADDITIONAL_GPU_ACCOUNTING.json').read_text())['conservative_additional_seconds']
initial=state['conservatively_rounded_total_with_prior_and_profiles_s']+extra
cap=min(2000,7200-initial-60)
activation={'registered_utc':datetime.now(UTC).isoformat(),'first_study_and_prior_accounted_s':initial,'available_allocated_s':cap,'minimum_required_s':1800,'quality_results_used':False,'activated':cap>=1800}
(root/'ACTIVATION.json').write_text(json.dumps(activation,indent=2)+'\n');print('ACTIVATION',activation,flush=True)
if not activation['activated']:
 (root/'DEFERRED.json').write_text(json.dumps({'reason':'insufficient remaining user GPU budget before any holdout result','activation':activation},indent=2)+'\n');raise SystemExit(0)
ledger={'initial_accounted_total_s':initial,'allocated_phase_s':cap,'phase_outer_s':0.,'jobs':[]}
for seed in protocol['seeds']:
 for cost in protocol['cost_grid']:
  out=root/f's{seed}_c{cost}';assert not out.exists();remaining=cap-ledger['phase_outer_s']
  if remaining<=0:raise RuntimeError('holdout budget exhausted')
  cmd=[str(r/'.venvs/flowmol3_venv/bin/python'),'tools/cifar_consistent_candidate_20261103.py','--protocol',str(root/'PROTOCOL.json'),'--out',str(out),'--seed',str(seed),'--cost',str(cost)]
  tic=time.monotonic()
  with (root/(out.name+'.log')).open('w') as log:
   try:z=subprocess.run(cmd,env=e,stdout=log,stderr=subprocess.STDOUT,timeout=min(600,remaining));code=z.returncode
   except subprocess.TimeoutExpired:code=124
  elapsed=time.monotonic()-tic;ledger['phase_outer_s']+=elapsed
  ledger['jobs'].append({'seed':seed,'cost':cost,'argv':cmd,'outer_wall_s':elapsed,'exit_code':code})
  (root/'RUN_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print(out.name,code,elapsed,flush=True)
  if code:raise SystemExit(code)
ledger['complete']=True;ledger['conservative_total_gpu_accounted_s']=initial+int(ledger['phase_outer_s']+1);assert ledger['conservative_total_gpu_accounted_s']<=7200
(root/'RUN_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print('ALL_HOLDOUT_COMPLETE',ledger['conservative_total_gpu_accounted_s'],flush=True)
