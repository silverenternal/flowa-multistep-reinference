from pathlib import Path
import json,numpy as np,time
from adaptive_reflow.eval.fid import compute_frechet_distance
r=Path('/home/hugo/codes/flowa-multistep-reinference');p=r/'verification_outputs/cifar-baseline-gate-20261103';start=time.monotonic()
z=np.load(p/'tfport_features.npz');ref=z['reference'].astype(np.float64);rng=np.random.default_rng(20261103);ref=ref[rng.permutation(len(ref))]
def fid(a,b):return float(compute_frechet_distance(mu_s=a.mean(0),sigma_s=np.cov(a,rowvar=False),mu_r=b.mean(0),sigma_r=np.cov(b,rowvar=False)))
rows=[]
for n in [1000,2000,5000]:
 value=fid(ref[:n],ref[n:]);rows.append({'real_A':n,'real_B':len(ref)-n,'fid':value});print(rows[-1],flush=True)
out={'purpose':'Independent metric resolution diagnostic after initial numerical threshold failed; no framework outcome viewed or generated on CIFAR','permutation_seed':20261103,'feature_family':'TF-port InceptionV3','disjoint_real_splits':rows,'generated1000_vs_real10000_fid':json.loads((p/'RESULT.json').read_text())['baseline_fid_tfport'],'wall_s':time.monotonic()-start,'note':'Real-real FID is a finite-sample calibration, not a quantity to subtract as an unbiased correction.'};(p/'REAL_REAL_CALIBRATION.json').write_text(json.dumps(out,indent=2)+'\n')
