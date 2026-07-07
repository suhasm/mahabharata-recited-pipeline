#!/usr/bin/env python3
"""Resumable, 4-GPU Mahabharata render driver. Runs ON the A40 container.
Idempotent: skips clips whose wav already exists. One pass = filter undone ->
split round-robin across GPUs -> launch one render.py per GPU (shared outdir) ->
wait -> concatenate any now-complete adhyayas. Safe to re-run after a container cycle.
"""
import os, sys, json, subprocess, glob, time
ROOT="/workspace/mbh_render"
WAVS=f"{ROOT}/wavs"; SUB=f"{ROOT}/sub"; ADH=f"{ROOT}/adhyaya"; LOG=f"{ROOT}/logs"
SRC="/workspace/vagdhenu/src"; BIG="/workspace/vagdhenu/BigVGAN"
NGPU=4
for d in (WAVS,SUB,ADH,LOG): os.makedirs(d,exist_ok=True)

def done_set():
    return set(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f"{WAVS}/*.wav"))

def render_pass():
    allc=json.load(open(f"{ROOT}/mbh_global_shard.json"))
    have=done_set()
    todo=[c for c in allc if c["id"] not in have]
    print(f"[drive] total={len(allc)} done={len(have)} todo={len(todo)}",flush=True)
    if not todo: return 0
    # round-robin split
    subs=[[] for _ in range(NGPU)]
    for i,c in enumerate(todo): subs[i%NGPU].append(c)
    procs=[]
    for g in range(NGPU):
        if not subs[g]: continue
        sp=f"{SUB}/sub_gpu{g}.json"; json.dump(subs[g],open(sp,"w"),ensure_ascii=False)
        env=os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"]=str(g)
        env["PYTHONPATH"]=f"{SRC}:{BIG}"
        env["CHAMP_ROOT"]="/workspace/vagdhenu/models"
        lf=open(f"{LOG}/gpu{g}.log","a")
        p=subprocess.Popen(["python",f"{SRC}/render.py","--shard",sp,"--outdir",WAVS,
                            "--results",f"{ROOT}/results_gpu{g}.json"],
                           env=env,stdout=lf,stderr=subprocess.STDOUT,cwd=ROOT)
        procs.append((g,p)); print(f"[drive] launched GPU{g} on {len(subs[g])} clips pid={p.pid}",flush=True)
    for g,p in procs: p.wait(); print(f"[drive] GPU{g} exited rc={p.returncode}",flush=True)
    return len(todo)

def concat_complete():
    """Concatenate every adhyaya whose clips are all present, if not already built."""
    import soundfile as sf, numpy as np
    allc=json.load(open(f"{ROOT}/mbh_global_shard.json"))
    have=done_set()
    byadh={}
    for c in allc: byadh.setdefault((c["parva"],c["adhyaya"]),[]).append(c["id"])
    SR=24000; gap=np.zeros(int(0.45*SR),dtype=np.float32); built=0
    for (pv,ad),ids in sorted(byadh.items()):
        outp=f"{ADH}/mbh_{pv:02d}_adh_{ad:03d}.wav"
        if os.path.exists(outp): continue
        if not all(i in have for i in ids): continue   # not finished yet
        segs=[]
        for i in ids:
            a,_=sf.read(f"{WAVS}/{i}.wav"); segs.append(a.astype(np.float32)); segs.append(gap)
        sf.write(outp,np.concatenate(segs),SR); built+=1
    print(f"[drive] concat: {built} new adhyaya files ({len(glob.glob(ADH+'/*.wav'))} total)",flush=True)

if __name__=="__main__":
    n=render_pass()
    concat_complete()
    # exit 0 if fully done, 2 if work remains (supervisor re-runs)
    remaining=len([c for c in json.load(open(f"{ROOT}/mbh_global_shard.json")) if c["id"] not in done_set()])
    print(f"[drive] pass complete, remaining={remaining}",flush=True)
    sys.exit(0 if remaining==0 else 2)
