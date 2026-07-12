#!/usr/bin/env python3
"""Per-element timestamps for every MBH marked adhyaya, mirroring splice_par.py exactly:
head[bell@0.1, opening@1.2] + 0.35 + bell + 0.45 + body(verse+0.45 each) + 0.6 + closing + 0.35 + bell + 0.3
Verse durations come from render results json where available, else wav headers.
Runs ON the pod. Writes /workspace/mbh_timestamps.json (+.csv).
"""
import json, os, glob, wave, csv

SR = 24000
ROOT = "/workspace/mbh_render"
PRE, ANN_AT, G1, G2, G3, G4, TAIL, VGAP = 0.1, 1.2, 0.35, 0.45, 0.6, 0.35, 0.3, 0.45

def wav_dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()

bell_d = wav_dur(f"{ROOT}/markers/bell_ref_short.wav")
print(f"bell: {bell_d:.3f}s", flush=True)

# verse durations: prefer render results (id -> dur), fall back to headers
dur = {}
for rf in glob.glob(f"{ROOT}/results_gpu*.json") + glob.glob(f"{ROOT}/markers/*results*.json"):
    try:
        for r in json.load(open(rf)):
            if isinstance(r, dict) and "id" in r and "dur" in r:
                dur[r["id"]] = float(r["dur"])
    except Exception as e:
        print(f"skip {rf}: {e}", flush=True)
print(f"durations from results: {len(dur)}", flush=True)

allc = json.load(open(f"{ROOT}/mbh_global_shard.json"))
byadh = {}
for c in allc:
    byadh.setdefault((c["parva"], c["adhyaya"]), []).append(c["id"])  # manifest order == final_concat order

fname = {}
for p in glob.glob(f"{ROOT}/adhyaya_mp3/*.mp3"):
    b = os.path.basename(p)
    fname[(int(b[4:6]), int(b[11:14]))] = b

missing_hdr = 0
out = {}
for (pv, ad), ids in sorted(byadh.items()):
    rows = []
    def add(cid, kind, start, d):
        rows.append({"id": cid, "kind": kind, "start": round(start, 3), "end": round(start + d, 3)})
    op_d = wav_dur(f"{ROOT}/markers/wavs/op_{pv:02d}_{ad:03d}.wav")
    cl_d = wav_dur(f"{ROOT}/markers/wavs/cl_{pv:02d}_{ad:03d}.wav")
    add("bell", "bell", PRE, bell_d)
    add(f"op_{pv:02d}_{ad:03d}", "opening", ANN_AT, op_d)
    head = max(ANN_AT + op_d, PRE + bell_d)
    t = head + G1
    add("bell", "bell", t, bell_d); t += bell_d + G2
    for cid in ids:
        d = dur.get(cid)
        if d is None:
            d = wav_dur(f"{ROOT}/wavs/{cid}.wav"); missing_hdr += 1
        add(cid, "verse", t, d); t += d + VGAP
    t += G3  # body (verse+VGAP each, incl. last) ends at t; then the 0.6s silence
    add(f"cl_{pv:02d}_{ad:03d}", "colophon", t, cl_d); t += cl_d + G4
    add("bell", "bell", t, bell_d); t += bell_d + TAIL
    out[fname.get((pv, ad), f"mbh_{pv:02d}_adh_{ad:03d}.mp3")] = {"total_s": round(t, 3), "elements": rows}

json.dump(out, open("/workspace/mbh_timestamps.json", "w"), ensure_ascii=False)
with open("/workspace/mbh_timestamps.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "element_id", "kind", "start_s", "end_s"])
    for fn, d in out.items():
        for r in d["elements"]:
            w.writerow([fn, r["id"], r["kind"], r["start"], r["end"]])
print(f"TIMESTAMPS_DONE files={len(out)} rows={sum(len(d['elements']) for d in out.values())} header_fallbacks={missing_hdr}", flush=True)
