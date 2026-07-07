
import os, glob, re, json, numpy as np, soundfile as sf
from scipy.signal import resample_poly

SR=24000
ADH="/workspace/mbh_render/adhyaya"
ANN="/workspace/mbh_render/markers/wavs"
OUT="/workspace/mbh_render/adhyaya_marked"
BELL="/workspace/mbh_render/markers/bell_ref_short.wav"
os.makedirs(OUT, exist_ok=True)

bell,bsr = sf.read(BELL)
if bsr!=SR:
    bell = resample_poly(bell, SR, bsr, axis=0)
if bell.ndim==1: bell=np.stack([bell,bell],1)
bell=bell.astype(np.float32)
m=np.abs(bell).max(); bell=bell/m*0.9 if m>0 else bell

def pn(x,t=0.95):
    m=np.abs(x).max(); return (x/m*t).astype(np.float32) if m>0 else x
def st(x): return x if x.ndim==2 else np.stack([x,x],1)
def sil(sec): return np.zeros((int(sec*SR),2),np.float32)
def load(p):
    a,sr=sf.read(p)
    if a.ndim==2: a=a.mean(1)
    if sr!=SR: a=resample_poly(a,SR,sr)
    return a.astype(np.float32)
def overlay(base,ins,at):
    end=at+len(ins)
    if end>len(base): base=np.concatenate([base,np.zeros((end-len(base),2),np.float32)])
    base[at:end]+=ins; return base

files=sorted(glob.glob(f"{ADH}/mbh_*_adh_*.wav"))
done=0; skipped=[]; fixed=[]
for f in files:
    mm=re.match(r".*mbh_(\d+)_adh_(\d+)\.wav$", f)
    pv,adh=int(mm.group(1)),int(mm.group(2))
    tag=f"{pv:02d}_{adh:03d}"
    outp=f"{OUT}/mbh_{pv:02d}_adh_{adh:03d}.wav"
    if os.path.exists(outp): 
        done+=1; continue
    opf=f"{ANN}/op_{tag}.wav"; clf=f"{ANN}/cl_{tag}.wav"
    if not (os.path.exists(opf) and os.path.exists(clf)):
        skipped.append(tag); continue
    # verses; if 0-byte (corrupt P13A01) try re-concat from clips
    try:
        body=load(f)
        if len(body)<SR*0.2: raise ValueError("too short")
    except Exception:
        skipped.append(tag+"(corrupt-body)"); continue
    r_body=np.sqrt((body**2).mean())+1e-9
    op=st(load(opf)); r=np.sqrt((op**2).mean()); op=op*(r_body/r) if r>0 else op
    cl=st(load(clf)); r=np.sqrt((cl**2).mean()); cl=cl*(r_body/r) if r>0 else cl
    body=st(body)
    ann_at=int(1.2*SR); preroll=int(0.1*SR)
    head=np.zeros((ann_at+len(op),2),np.float32)
    head=overlay(head,bell,preroll); head=overlay(head,op,ann_at)
    seq=np.concatenate([head, sil(0.35), bell, sil(0.45),
                        body, sil(0.6),
                        cl, sil(0.35), bell, sil(0.3)])
    sf.write(outp, pn(seq,0.95), SR)
    done+=1
    if done%200==0: print(f"spliced {done}", flush=True)

print(f"SPLICE DONE spliced_or_present={done} skipped={len(skipped)}")
if skipped: print("skipped:", skipped[:30])
