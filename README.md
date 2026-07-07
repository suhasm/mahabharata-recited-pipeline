# Mahābhārata Critical Edition — Recitation Pipeline

Scripts, data, and documentation to (re)generate a complete neural-TTS Sanskrit
recitation of the **Mahābhārata Critical Edition** (BORI / Sukthankar) — all 18
parvans, 1,995 adhyāyas, ~232 hours — with traditional recitation markers (opening
bell + spoken chapter announcement + verses + closing colophon + closing bell).

**Start with [`CLAUDE.md`](CLAUDE.md)** — it documents the full architecture, the
compute environment, every pipeline stage, and the pitfalls, and is written so an AI
agent or a human can resume the project cold.

## Layout
```
CLAUDE.md                     full project memory / resume guide  ← read this first
archive_org_metadata.md       ready-to-paste archive.org item metadata
README.md                     this file
scripts/
  markers/  build_ann_shard.py, ann_drive.py, ann_supervisor.sh,
            splice.py, splice_par.py, splice_par_launch.sh
  naming/   build_filenames.py, do_rename_inplace.py
  mp3/      mp3_enc.py, mp3_launch.sh
data/
  mbh_adhyaya_filenames.csv   CE adhyaya -> descriptive filename (all 1,995 rows)
  mbh_marker_meta.json        per-chapter ordinal colophons + per-parva frames (sandhi done)
  rename_map.tsv              old_filename -> new_filename
  ann_shard.sample.json       example announcement shard
assets/
  bell_ref_short.wav          intro/outro bell  ← SEE rights note below
```

## Rights & provenance (read before redistributing)
Three layers apply — see the License section of `archive_org_metadata.md` and §6 of
`CLAUDE.md`:
1. **Audio** (the recitation) — yours.
2. **CE text** — the BORI critical edition is an editorial work; confirm your rights.
3. **Bell sample** — currently extracted from a copyrighted commercial recording,
   **not cleared for redistribution**. Replace with a cleared/self-recorded bell and
   re-run the splice + mp3 stages before publishing.

## What's included
The full `vagdhenu/` render code and reference bank, all render/marker/naming/mp3
scripts, and every work-list and mapping. The **only** missing piece is the ~3.1 GB
of model weights (`voice_steer_*.pt`, `voice_armA_*.pt`, `voc_bigvgan_*.pth`), which
exceed GitHub's 100 MB file limit — add them via Git LFS or a separate release to
make the repo able to regenerate audio. See §7 of `CLAUDE.md`.
