
import json, os, glob, sys
import soundfile as sf, numpy as np
ROOT="/workspace/mbh_render"; WAVS=f"{ROOT}/wavs"; ADH=f"{ROOT}/adhyaya"
allc=json.load(open(f"{ROOT}/mbh_global_shard.json"))
have=set(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(WAVS+"/*.wav"))
byadh={}
for c in allc: byadh.setdefault((c["parva"],c["adhyaya"]),[]).append(c["id"])
SR=24000; gap=np.zeros(int(0.45*SR),dtype=np.float32); built=0; skipped=0
for (pv,ad),ids in sorted(byadh.items()):
    outp=f"{ADH}/mbh_{pv:02d}_adh_{ad:03d}.wav"
    if os.path.exists(outp): continue
    if not all(i in have for i in ids): skipped+=1; continue
    segs=[]
    for i in ids:
        a,_=sf.read(f"{WAVS}/{i}.wav"); segs.append(a.astype(np.float32)); segs.append(gap)
    tmp=outp+".tmp.wav"
    sf.write(tmp,np.concatenate(segs),SR); os.replace(tmp,outp); built+=1
    if built%50==0: print(f"built {built}...", flush=True)
total=len(glob.glob(ADH+"/*.wav"))
print(f"DONE built={built} skipped_blocked={skipped} adhyaya_total={total}", flush=True)
