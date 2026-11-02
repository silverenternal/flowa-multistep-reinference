from pathlib import Path
import sys,json,hashlib,time
import numpy as np
r=Path('/home/hugo/codes/flowa-multistep-reinference');sys.path.insert(0,str(r))
from tools.cifar_study_metrics_20261103 import kernel_rows,kernel_score
p=r/'verification_outputs/cifar-study-20261103';start=time.monotonic()
source=r/'verification_outputs/cifar-baseline-gate-20261103/tfport_features.npz'
ref=np.load(source)['reference'];np.savez_compressed(p/'reference_features.npz',reference=ref)
full=ref.astype(np.float64);constant=float(kernel_rows(full,full,self_kernel=True).mean())
rows=[]
for seed in range(202611030,202611035):
 a=np.random.default_rng(seed).permutation(len(full));x,y=full[a[:1000]],full[a[1000:]]
 xx=kernel_rows(x,x,self_kernel=True);xy=kernel_rows(x,y);yy=float(kernel_rows(y,y,self_kernel=True).mean())
 rows.append({'permutation_seed':seed,'n_a':len(x),'n_b':len(y),'kid_unscaled':kernel_score(xx,xy,yy)})
result={'source':str(source.relative_to(r)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'reference_sha256':hashlib.sha256((p/'reference_features.npz').read_bytes()).hexdigest(),
        'feature_family':'pytorch_fid TF-port InceptionV3 2048 pool3','reference_shape':list(ref.shape),
        'reference_self_kernel':constant,'real_real_diagnostics':rows,'wall_cpu_s':time.monotonic()-start,
        'scope':'CPU metric calibration using real features only; before new pilot or method generation. Permutations are correlated, not five independent datasets. No FID-bias subtraction and no passing the previous <10 gate.'}
(p/'REFERENCE_STATISTICS.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
