from pathlib import Path
import sys,ast,json,hashlib,subprocess,time,types
from datetime import datetime,UTC
r=Path('/home/hugo/codes/flowa-multistep-reinference');sys.path.insert(0,str(r))
p=r/'verification_outputs/cifar-study-20261103';out=p/'euler_reference_parity';out.mkdir(exist_ok=False)
source=Path('/tmp/flowa-rf-official-20261103/ImageGeneration/sampling.py')
(out/'METADATA.json').write_text(json.dumps({'registered_utc':datetime.now(UTC).isoformat(),'argv':sys.argv,'device':'cuda:0','n':2,'seed':20261103,'steps':25,'wall_limit_s':120,'purpose':'Original Euler sampling-loop correctness; no metric or model selection','source_path':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'environment':sys.executable,'gpu_snapshot':subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.free,utilization.gpu','--format=csv,noheader'],text=True)},indent=2)+'\n')
start=time.monotonic()
import torch,numpy as np
from adaptive_reflow.adapters._gnobitab_ddpmpp import load_gnobitab_rf_cifar_unet
from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
device='cuda:0'
model=load_gnobitab_rf_cifar_unet(_extract_checkpoint_state_dict(torch.load(r/'data/cifar10_rf.pth',map_location='cpu',weights_only=False))).to(device).eval()
tree=ast.parse(source.read_text());outer=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='get_rectified_flow_sampler');fn=next(x for x in outer.body if isinstance(x,ast.FunctionDef) and x.name=='euler_sampler')
namespace=dict(torch=torch,np=np,sde=types.SimpleNamespace(sample_N=25,T=1.,noise_scale=1.,sigma_t=lambda _t:0.),shape=(2,3,32,32),device=device,inverse_scaler=lambda x:x,mutils=types.SimpleNamespace(get_model_fn=lambda model,train:model))
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)
z=torch.as_tensor(np.random.default_rng(20261103).standard_normal((2,3,32,32)).astype(np.float32),device=device)
with torch.inference_mode():
 expected,nfe=namespace['euler_sampler'](model.net,z=z.clone())
 actual=z.clone()
 for i in range(25):actual=actual+model(actual,torch.full((2,),.001+i/25*.999,device=device))/25
error=float((actual-expected).abs().max());assert nfe==25 and error<1e-5,(nfe,error)
(out/'RESULT.json').write_text(json.dumps({'n_processed':2,'n_skipped':0,'source_nfe':nfe,'our_velocity_calls':25,'max_abs_difference':error,'pass':True,'gpu_bearing_wall_s':time.monotonic()-start,'scope':'Same exact model and initial physical states; original RF Euler source function vs new driver arithmetic. Supplements previous original-network forward parity.'},indent=2)+'\n')
(p/'ADDITIONAL_GPU_ACCOUNTING.json').write_text(json.dumps({'registered_reason':'Independent original Euler-loop parity, no quality or seed topup','conservative_additional_seconds':60,'user_total_gpu_seconds':7200,'combined_maximum_with_prior_profiles_and_locked_study_cap':6540},indent=2)+'\n')
print(error,time.monotonic()-start)
