from pathlib import Path
import subprocess,os,json,time
r=Path('/home/hugo/codes/flowa-multistep-reinference');os.chdir(r);root=r/'verification_outputs/component-study-20261103'
e=os.environ.copy();e.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONPATH=str(r))
used=json.loads((root/'pilot_w16e1_5k_s42_n64/results.json').read_text())['wall_s'];jobs=[]
for ck in ['w16e1_5k','production']:
 for seed in [42,43,44]:
  out=root/f'{ck}_s{seed}'
  if used>=1700:raise RuntimeError('study budget exhausted; no seed topup allowed')
  cmd=[str(r/'.venvs/flowmol3_venv/bin/python'),'tools/component_study_20261103.py','--checkpoint',ck,'--seed',str(seed),'--n','1000','--device','cuda:0','--protocol',str(root/'PROTOCOL.json'),'--out',str(out)]
  tick=time.monotonic()
  with (root/f'{ck}_s{seed}.log').open('w') as log:
   p=subprocess.run(cmd,env=e,stdout=log,stderr=subprocess.STDOUT,timeout=min(600,1800-used))
  elapsed=time.monotonic()-tick;used+=elapsed;jobs.append({'checkpoint':ck,'seed':seed,'exit_code':p.returncode,'wall_s':elapsed,'argv':cmd})
  (root/'RUN_LEDGER.json').write_text(json.dumps({'jobs':jobs,'conservative_gpu_bearing_wall_s':used,'budget_phase_s':1800},indent=2)+'\n');print(ck,seed,p.returncode,round(elapsed,1),flush=True)
  if p.returncode:raise SystemExit(p.returncode)
print('COMPLETE',len(jobs),round(used,1),flush=True)
