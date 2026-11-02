from pathlib import Path
import sys,time,json
r=Path('/home/hugo/codes/flowa-multistep-reinference');sys.path.insert(0,str(r))
import torch,numpy as np
from adaptive_reflow.adapters._gnobitab_ddpmpp import load_gnobitab_rf_cifar_unet
from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict
from tools.cifar_matched_frontier_20261103 import denoiser_value
p=r/'verification_outputs/cifar-study-20261103'
tick=time.monotonic();device='cuda:1';torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
model=load_gnobitab_rf_cifar_unet(_extract_checkpoint_state_dict(torch.load(r/'data/cifar10_rf.pth',map_location='cpu',weights_only=False))).to(device).eval()
x=torch.ones((32,3,32,32),device=device);t=torch.ones(32,device=device)*.5;sigma=torch.tensor(.3,device=device,dtype=torch.float64);y=x.double()
rows=[]
with torch.inference_mode():
 for _ in range(3):model(x,t)
 torch.cuda.synchronize()
 for kind in ['direct_async','direct_with_sync','bridge_GPU_scalar','bridge_CPU_scalar','direct_async_repeat']:
  tic=time.monotonic();a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);a.record()
  for _ in range(25):
   if kind.startswith('direct'):v=model(x,t)
   elif kind=='bridge_GPU_scalar':v=denoiser_value(model,y,sigma)
   else:
    st=1/(1+float(sigma));v=st*y+(1-st)*model((st*y).float(),torch.full((len(y),),st,device=device)).double()
   if kind=='direct_with_sync':torch.cuda.synchronize()
  b.record();torch.cuda.synchronize();rows.append({'kind':kind,'wall_s':time.monotonic()-tic,'cuda_ms':a.elapsed_time(b)});print(rows[-1],flush=True)
result={'rows':rows,'gpu_bearing_wall_s':time.monotonic()-tick,'scope':'implementation runtime only, no metric/model-selection evidence'}
(p/'BRIDGE_PROFILE.json').write_text(json.dumps(result,indent=2)+'\n')
