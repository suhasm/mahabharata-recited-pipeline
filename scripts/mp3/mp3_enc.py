
import os, glob, subprocess, sys
MOD=int(sys.argv[1]); RANK=int(sys.argv[2])
SRC="/workspace/mbh_render/adhyaya_marked"
DST="/workspace/mbh_render/adhyaya_mp3"
FFMPEG="/workspace/miniconda3/envs/audio/bin/ffmpeg"
os.makedirs(DST, exist_ok=True)
files=sorted(glob.glob(f"{SRC}/*.wav"))
files=[f for i,f in enumerate(files) if i%MOD==RANK]
done=0; fail=[]
for f in files:
    base=os.path.basename(f)[:-4]+".mp3"
    dp=os.path.join(DST,base)
    if os.path.exists(dp) and os.path.getsize(dp)>1000: continue
    # spoken word: 96k CBR stereo, keep 24k sample rate
    r=subprocess.run([FFMPEG,"-y","-loglevel","error","-i",f,
        "-codec:a","libmp3lame","-b:a","96k","-ar","24000",dp],
        capture_output=True, text=True)
    if r.returncode!=0 or not os.path.exists(dp): fail.append((base,r.stderr[:100])); continue
    done+=1
    if done%200==0: print(f"rank{RANK} {done}", flush=True)
print(f"rank{RANK} DONE encoded={done} fail={len(fail)} {fail[:3]}", flush=True)
