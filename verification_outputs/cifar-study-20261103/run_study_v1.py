from pathlib import Path
import subprocess,json,os,time
from datetime import datetime,UTC
r=Path('/home/hugo/codes/flowa-multistep-reinference');os.chdir(r)
p=r/'verification_outputs/cifar-study-20261103';protocol=json.loads((p/'PROTOCOL.json').read_text())
e=os.environ.copy();e.update(OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4',PYTHONPATH=str(r))
ledger={'user_total_gpu_budget_s':7200,'prior_accounted_s':360,'study_wall_cap_s':6000,'used_study_s':0.,'jobs':[]}
def job(n,seed,cost):
 out=p/(f'pilot_n{n}_s{seed}_c{cost}' if n!=1000 else f's{seed}_c{cost}')
 used=ledger['used_study_s']
 if used>=6000:raise RuntimeError('study budget exhausted')
 cmd=[str(r/'.venvs/flowmol3_venv/bin/python'),'tools/cifar_matched_frontier_20261103.py','--protocol',str(p/'PROTOCOL.json'),'--out',str(out),'--seed',str(seed),'--cost',str(cost),'--n',str(n),'--device','cuda:1']
 start=time.monotonic();registered=datetime.now(UTC).isoformat()
 with (p/(out.name+'.log')).open('w') as log:
  try:
   z=subprocess.run(cmd,env=e,stdout=log,stderr=subprocess.STDOUT,timeout=min(1200,6000-used));code=z.returncode
  except subprocess.TimeoutExpired:code=124
 elapsed=time.monotonic()-start;ledger['used_study_s']+=elapsed
 ledger['jobs'].append({'registered_utc':registered,'n':n,'seed':seed,'cost':cost,'argv':cmd,'outer_wall_s':elapsed,'exit_code':code})
 (p/'RUN_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print(out.name,code,elapsed,flush=True)
 if code:raise SystemExit(code)
 return json.loads((out/'results.json').read_text())
pilot=job(32,42,25)
# Runtime guard only, no selection using any quality score.
generation=sum(x['generation_wall_s'] for x in pilot['arms'].values())
projected=generation*(1000/32)*sum(protocol['cost_grid'])/25*3+12*45+ledger['used_study_s']
(p/'PILOT_RUNTIME_GUARD.json').write_text(json.dumps({'pilot_generation_s':generation,'conservative_scientific_projection_s':projected,'quality_scores_used_for_gate':False,'budget_s':6000,'pass':projected<5700},indent=2)+'\n')
if projected>=5700:raise RuntimeError('runtime projection exceeds locked budget; no scientific run launched')
for seed in protocol['seeds']:
 for cost in protocol['cost_grid']:job(1000,seed,cost)
ledger['complete']=True;ledger['conservatively_rounded_total_with_prior_s']=360+int(ledger['used_study_s']+1)
(p/'RUN_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print('ALL_COMPLETE',ledger['used_study_s'],flush=True)
