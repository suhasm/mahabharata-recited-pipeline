
import os, glob, re, sys, numpy as np, soundfile as sf
from scipy.signal import resample_poly
MOD=int(sys.argv[1]); RANK=int(sys.argv[2])
SR=24000
ADH="/workspace/mbh_render/adhyaya"; ANN="/workspace/mbh_render/markers/wavs"
OUT="/workspace/mbh_render/adhyaya_marked"; BELL="/workspace/mbh_render/markers/bell_ref_short.wav"
os.makedirs(OUT, exist_ok=True)
bell,bsr=sf.read(BELL)
if bsr!=SR: bell=resample_poly(bell,SR,bsr,axis=0)
if bell.ndim==1: bell=np.stack([bell,bell],1)
bell=bell.astype(np.float32); m=np.abs(bell).max(); bell=bell/m*0.9 if m>0 else bell
def pn(x,t=0.95):
    m=np.abs(x).max(); return (x/m*t).astype(np.float32) if m>0 else x
def st(x): return x if x.ndim==2 else np.stack([x,x],1)
def sil(s): return np.zeros((int(s*SR),2),np.float32)
def load(p):
    a,sr=sf.read(p); a=a.mean(1) if a.ndim==2 else a
    if sr!=SR: a=resample_poly(a,SR,sr)
    return a.astype(np.float32)
def ov(base,ins,at):
    e=at+len(ins)
    if e>len(base): base=np.concatenate([base,np.zeros((e-len(base),2),np.float32)])
    base[at:e]+=ins; return base
files=sorted(glob.glob(f"{ADH}/mbh_*_adh_*.wav"))
files=[f for i,f in enumerate(files) if i%MOD==RANK]
done=0; skip=[]
for f in files:
    mm=re.match(r".*mbh_(\d+)_adh_(\d+)\.wav$",f); pv,adh=int(mm.group(1)),int(mm.group(2))
    tag=f"{pv:02d}_{adh:03d}"; outp=f"{OUT}/mbh_{pv:02d}_adh_{adh:03d}.wav"
    if os.path.exists(outp) and os.path.getsize(outp)>1000: continue
    opf=f"{ANN}/op_{tag}.wav"; clf=f"{ANN}/cl_{tag}.wav"
    if not(os.path.exists(opf) and os.path.exists(clf)): skip.append(tag+"(noann)"); continue
    try:
        body=load(f)
        if len(body)<SR*0.2: raise ValueError
    except Exception: skip.append(tag+"(body)"); continue
    rb=np.sqrt((body**2).mean())+1e-9
    op=st(load(opf)); r=np.sqrt((op**2).mean()); op=op*(rb/r) if r>0 else op
    cl=st(load(clf)); r=np.sqrt((cl**2).mean()); cl=cl*(rb/r) if r>0 else cl
    body=st(body); ann_at=int(1.2*SR); pre=int(0.1*SR)
    head=np.zeros((ann_at+len(op),2),np.float32); head=ov(head,bell,pre); head=ov(head,op,ann_at)
    seq=np.concatenate([head,sil(0.35),bell,sil(0.45),body,sil(0.6),cl,sil(0.35),bell,sil(0.3)])
    sf.write(outp,pn(seq,0.95),SR); done+=1
print(f"rank{RANK} done={done} skip={len(skip)} {skip[:10]}", flush=True)
