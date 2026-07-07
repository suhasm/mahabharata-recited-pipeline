
import json, os, subprocess, sys
SHARD="/workspace/mbh_render/markers/ann_shard_full.json"
OUT="/workspace/mbh_render/markers/wavs"
os.makedirs(OUT, exist_ok=True)
shard=json.load(open(SHARD))
# skip already-rendered
todo=[e for e in shard if not os.path.exists(os.path.join(OUT,e["out"]))]
print(f"total={len(shard)} todo={len(todo)}", flush=True)
if not todo:
    print("ALL DONE"); sys.exit(0)
# split into 4
N=4
parts=[todo[i::N] for i in range(N)]
procs=[]
for g in range(N):
    sp=f"/workspace/mbh_render/markers/sub_gpu{g}.json"
    json.dump(parts[g], open(sp,"w"), ensure_ascii=False)
    env=dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"]=str(g)
    env["PYTHONPATH"]="/workspace/vagdhenu/src:/workspace/vagdhenu/BigVGAN"
    env["CHAMP_ROOT"]="/workspace/vagdhenu/models"
    logf=open(f"/workspace/mbh_render/markers/render_gpu{g}.log","w")
    p=subprocess.Popen(["python","/workspace/vagdhenu/src/render.py",
        "--shard",sp,"--outdir",OUT,"--results",f"/workspace/mbh_render/markers/res_gpu{g}.json"],
        env=env, stdout=logf, stderr=subprocess.STDOUT)
    procs.append((g,p))
    print(f"launched gpu{g} with {len(parts[g])} clips", flush=True)
rc=0
for g,p in procs:
    r=p.wait(); print(f"gpu{g} exited rc={r}", flush=True); rc=rc or r
done=len([e for e in shard if os.path.exists(os.path.join(OUT,e["out"]))])
print(f"after pass: {done}/{len(shard)} rendered", flush=True)
sys.exit(0 if done==len(shard) else 2)
