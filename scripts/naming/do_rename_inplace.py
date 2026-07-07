
import csv, os
MAP="/workspace/mbh_render/markers/rename_map.tsv"
D="/workspace/mbh_render/adhyaya_marked"
done=0; miss=[]; already=0; man=[]
with open(MAP) as f:
    for row in csv.DictReader(f, delimiter="\t"):
        old=row["old_filename"]; new=row["new_filename"]
        sp=os.path.join(D,old); dp=os.path.join(D,new)
        man.append((old,new))
        if os.path.exists(dp): already+=1; continue
        if not os.path.exists(sp): miss.append(old); continue
        os.rename(sp,dp); done+=1   # in-place, zero extra bytes
# manifest lives alongside; write to markers dir to avoid touching data dir naming
with open("/workspace/mbh_render/markers/manifest_named.tsv","w") as f:
    f.write("old_filename\tnew_filename\n")
    for o,n in man: f.write(f"{o}\t{n}\n")
wavs=len([x for x in os.listdir(D) if x.endswith(".wav")])
print(f"RENAME_INPLACE done={done} already={already} missing={len(miss)} total_wavs_now={wavs}")
if miss: print("missing:", miss[:10])
