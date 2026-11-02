from pathlib import Path
from datetime import datetime,UTC
import sys,json,hashlib,time
r=Path('/home/hugo/codes/flowa-multistep-reinference');sys.path.insert(0,str(r))
import torch
from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict
start=time.monotonic();raw_path=r/'data/rectified_flow_cifar10.pth';clean_path=r/'data/cifar10_rf.pth'
raw=torch.load(raw_path,map_location='cpu',weights_only=False)
clean=_extract_checkpoint_state_dict(torch.load(clean_path,map_location='cpu',weights_only=False))
source=raw['model'];shadow=raw['ema']['shadow_params'];names=[k for k in source if not k.endswith('sigmas')]
assert len(names)==len(shadow)
failures=[]
for name,ema in zip(names,shadow,strict=True):
 key=name if name in clean else name.removeprefix('module.')
 if key not in clean or not torch.equal(clean[key],ema):failures.append(name)
assert not failures,failures
buffer_names=[k for k in source if k.endswith('sigmas')]
buffers={name:torch.equal(source[name],clean[name if name in clean else name.removeprefix('module.')]) for name in buffer_names}
result={'recorded_utc':datetime.now(UTC).isoformat(),'raw_path':str(raw_path.relative_to(r)),'clean_path':str(clean_path.relative_to(r)),'raw_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'clean_sha256':hashlib.sha256(clean_path.read_bytes()).hexdigest(),'parameters_compared':len(names),'parameters_bitwise_equal':len(names)-len(failures),'buffers_equal':buffers,'training_step':raw.get('step'),'ema_num_updates':raw['ema'].get('num_updates'),'ema_decay':raw['ema'].get('decay'),'wall_cpu_s':time.monotonic()-start,'scope':'Current cleaned inference tensors exactly match the available raw checkpoint EMA under the recorded extraction order. Does not independently authenticate remote download or reproduce published50k FID.'}
(r/'verification_outputs/cifar-study-20261103/WEIGHTS_LINEAGE_CHECK.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
