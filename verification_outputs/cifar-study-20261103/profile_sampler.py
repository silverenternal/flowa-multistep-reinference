from pathlib import Path
import sys,time,json
r=Path('/home/hugo/codes/flowa-multistep-reinference');sys.path.insert(0,str(r))
import torch,numpy as np
from adaptive_reflow.adapters._gnobitab_ddpmpp import load_gnobitab_rf_cifar_unet
from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict
from tools.cifar_matched_frontier_20261103 import RFDenoiser,official_sampler
p=r/'verification_outputs/cifar-study-20261103';start=time.monotonic();device='cuda:1'
model=load_gnobitab_rf_cifar_unet(_extract_checkpoint_state_dict(torch.load(r/'data/cifar10_rf.pth',map_location='cpu',weights_only=False))).to(device).eval()
source=p/'restart_source.py';sampler=official_sampler(source)
z=torch.ones((32,3,32,32),device=device);rows=[]
with torch.inference_mode():
 for _ in range(3):model(z,torch.ones(32,device=device)*.5)
 for kind in ['numpy_copy','torch_gpu','numpy_copy_repeat']:
  rng=np.random.default_rng(42);gen=torch.Generator(device=device).manual_seed(42)
  def noise(x):
   if kind=='torch_gpu':return torch.randn(x.shape,generator=gen,device=x.device,dtype=x.dtype)
   return torch.as_tensor(rng.standard_normal(tuple(x.shape)),device=x.device,dtype=x.dtype)
  torch.cuda.synchronize(device);tic=time.monotonic()
  x=sampler(RFDenoiser(model),z.double()/(999/1000),num_steps=9,sigma_min=.002,sigma_max=999,rho=7,S_noise=1.,restart_gamma=0.,S_churn=0.,randn_like=noise,restart_info='{"0":[3,2,0.06,0.30]}')
  torch.cuda.synchronize(device);rows.append({'noise_implementation':kind,'wall_s':time.monotonic()-tic});print(rows[-1],flush=True)
(p/'SAMPLER_PROFILE.json').write_text(json.dumps({'rows':rows,'gpu_bearing_wall_s':time.monotonic()-start,'scope':'runtime profiling; no score or configuration selection'},indent=2)+'\n')
