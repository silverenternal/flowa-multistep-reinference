from pathlib import Path
import subprocess,json,sys,os,hashlib,math,time
r=Path(sys.argv[1]).resolve();o=Path(sys.argv[2]).resolve();o.mkdir(exist_ok=True)
head=subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip();assert not subprocess.check_output(['git','-C',str(r),'status','--porcelain'],text=True).strip()
manifest=json.loads((r/'verification_outputs/ot-refresh-20261103/SCIENCE_HASHES.json').read_text())
for p,h in manifest.items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h,p
commands=[['tools/review_ot_refresh_20261103.py','--output-dir',str(o/'base'),'--max-records','73','--seed','20261103','--wall-seconds','180'],['tools/review_ot_refresh_robust_20261103.py','--output-dir',str(o/'robust'),'--max-records','27','--seed','20261103','--wall-seconds','60']]
tick=time.monotonic()
for cmd in commands:subprocess.run([sys.executable,*cmd],cwd=r,check=True)
maxerr=0.;n=0
for kind,source in [('base','results.json'),('robust','robust/results.json')]:
 a=json.loads((r/'verification_outputs/ot-refresh-20261103'/source).read_text());b=json.loads((o/kind/'results.json').read_text());assert a['passed'] and b['passed'];assert a['processed']==b['processed'];assert a['skipped']==b['skipped']==0
 for x,y in zip(a['rows'],b['rows'],strict=True):
  assert x.keys()==y.keys()
  for key in x:
   if type(x[key]) in (int,float):
    err=abs(x[key]-y[key]);maxerr=max(maxerr,err);assert err<1e-9,(kind,key,x[key],y[key])
   else:assert x[key]==y[key],key
  n+=1
assert n==100
z={'scientific_commit':head,'source_file_hashes_verified':len(manifest),'cases_replayed':n,'max_numeric_error':maxerr,'row_tolerance_absolute':1e-9,'wall_seconds':time.monotonic()-tick,'GPU_used':False,'scope':'Mac analytic CPU replay and hashes only; no image generation, novelty certificate or Mac full engineering suite','python':sys.version,'completed':True}
(o/'MAC_REPLAY.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps(z))
