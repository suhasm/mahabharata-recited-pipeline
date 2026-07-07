
import json, os, glob, re
meta = json.load(open("mbh_marker_meta.json"))
colophon = {int(k):v for k,v in meta["colophon"].items()}
parva    = {int(k):v for k,v in meta["parva"].items()}
frame    = {int(k):v for k,v in meta["closing_frame"].items()}
header   = {int(k):v for k,v in meta["header"].items()}

ADH = "/workspace/mbh_render/adhyaya"
files = sorted(glob.glob(f"{ADH}/mbh_*_adh_*.wav"))
items = []
for f in files:
    m = re.match(r".*mbh_(\d+)_adh_(\d+)\.wav$", f)
    pv, adh = int(m.group(1)), int(m.group(2))
    items.append((pv, adh))

# first adhyaya of each parva = min adh present in that parva
firsts = {}
for pv, adh in items:
    firsts[pv] = min(adh, firsts.get(pv, 10**9))

SEED = 60
shard = []
for pv, adh in items:
    col = colophon[adh]
    tag = f"{pv:02d}_{adh:03d}"
    # opening: header line only if first adhyaya of parva
    open_padas = ([header[pv]] if adh == firsts[pv] else []) + [f"अथ {col}"]
    shard.append({"id":f"op_{tag}","meter":"vasantatilaka","padas":open_padas,
                  "seed":SEED,"no_sandhi":True,"out":f"op_{tag}.wav"})
    # closing
    close = f"इति श्रीमन्महाभारते शतसाहस्रिकायां संहितायां {frame[pv]} {col}"
    shard.append({"id":f"cl_{tag}","meter":"vasantatilaka","padas":[close],
                  "seed":SEED,"no_sandhi":True,"out":f"cl_{tag}.wav"})

os.makedirs("/workspace/mbh_render/markers", exist_ok=True)
json.dump(shard, open("/workspace/mbh_render/markers/ann_shard_full.json","w"), ensure_ascii=False)
print("total adhyayas:", len(items))
print("shard entries (openings+closings):", len(shard))
print("first-of-parva:", {pv:firsts[pv] for pv in sorted(firsts)})
# sanity: show a few
for e in shard[:2] + shard[-2:]:
    print(e["id"], e["padas"])
