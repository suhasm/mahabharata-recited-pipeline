#!/usr/bin/env python3
"""
build_filenames.py — regenerate the CE-adhyaya -> descriptive-filename mapping.

Reads the two row-aligned TSVs from the mahabharata-align-copy repo and produces
mbh_adhyaya_filenames.csv (parva, adhyaya, subparva, full_title, old/new filename).

The two TSVs are POSITIONALLY ALIGNED (verified: 2120/2120 rows, Book matches
row-by-row). 5-full.tsv row i gives which CE adhyayas Ganguli-section i covers
(Skt_List); Ganguli-Dutt.tsv row i gives that section's sub-parvan (Section) and
descriptive Chapter name. Joining on CE adhyaya via Skt_List (NOT on the Dutt
chapter number, which does not line up with CE numbering) yields 100% coverage of
all 1,995 CE adhyayas.

Usage:
    python build_filenames.py /path/to/mahabharata-align-copy  out.csv
"""
import sys, ast, re, unicodedata
from collections import defaultdict
import pandas as pd

ALIGN_REPO = sys.argv[1] if len(sys.argv) > 1 else "mahabharata-align-copy"
OUT        = sys.argv[2] if len(sys.argv) > 2 else "mbh_adhyaya_filenames.csv"

# CE adhyaya counts per parva (the 1,995-file set)
OUR = {1:225,2:72,3:299,4:67,5:197,6:117,7:173,8:69,9:64,10:18,
       11:27,12:353,13:154,14:96,15:47,16:9,17:3,18:5}
PARVA = {1:"Adi",2:"Sabha",3:"Aranyaka",4:"Virata",5:"Udyoga",6:"Bhishma",
         7:"Drona",8:"Karna",9:"Shalya",10:"Sauptika",11:"Stri",12:"Shanti",
         13:"Anushasana",14:"Ashvamedhika",15:"Ashramavasika",16:"Mausala",
         17:"Mahaprasthanika",18:"Svargarohana"}

full = pd.read_csv(f"{ALIGN_REPO}/mappings/ce-ganguli/5-full.tsv", sep="\t", dtype=str).fillna("")
gd   = pd.read_csv(f"{ALIGN_REPO}/mappings/Ganguli-Dutt.tsv",       sep="\t", dtype=str).fillna("")
assert len(full) == len(gd), "TSVs not the same length — alignment assumption broken"

def parse_skt(s):
    try: return ast.literal_eval(s)
    except Exception: return []
full["skt"] = full["Skt_List"].map(parse_skt)
book = pd.to_numeric(full["Book"], errors="coerce")

ce_names = defaultdict(list); ce_sect = defaultdict(list)
for i in range(len(full)):
    b = book.iloc[i]
    if pd.isna(b): continue
    b = int(b)
    nm = gd.iloc[i]["Chapter name"].strip()
    sc = gd.iloc[i]["Section"].strip()
    for a in sorted(set(t[0] for t in full.iloc[i]["skt"] if t and t[0] is not None)):
        if nm: ce_names[(b,a)].append(nm)
        if sc: ce_sect[(b,a)].append(sc)

def ascii_slug(s, maxlen=60):
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+","-", s).strip("-")
    if len(s) <= maxlen: return s
    cut = s[:maxlen]
    return (cut[:cut.rfind("-")] if "-" in cut else cut).strip("-")

def sub_slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+","-", s).strip("-")

def join_uniq(xs):
    out=[]
    for x in xs:
        if x not in out: out.append(x)
    return " / ".join(out)

rows=[]
for b in range(1,19):
    for a in range(1, OUR[b]+1):
        names = ce_names.get((b,a), []); sects = ce_sect.get((b,a), [])
        full_title = join_uniq(names)
        first_title = names[0] if names else ""
        first_sub   = sects[0] if sects else ""
        sslug = sub_slug(first_sub); tslug = ascii_slug(first_title, 60)
        parts = [f"mbh_{b:02d}_adh_{a:03d}"]
        if sslug: parts.append(sslug)
        if tslug: parts.append(tslug)
        rows.append(dict(
            parva_num=b, parva_name=PARVA[b], adhyaya=a,
            subparva=first_sub, full_title=full_title,
            old_filename=f"mbh_{b:02d}_adh_{a:03d}.wav",
            new_filename="__".join(parts)+".wav",
        ))
df = pd.DataFrame(rows)
df["new_len"] = df["new_filename"].str.len()
assert df["new_filename"].duplicated().sum() == 0, "filename collision!"
assert len(df) == sum(OUR.values()) == 1995
df.to_csv(OUT, index=False)
print(f"wrote {OUT}: {len(df)} rows, max filename len {df['new_len'].max()}")
