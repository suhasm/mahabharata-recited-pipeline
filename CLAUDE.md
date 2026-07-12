# CLAUDE.md — Mahābhārata Critical Edition Recitation Pipeline

This file orients an AI agent (or a human) resuming this project. It records the
full architecture, where everything lives, how each stage runs, and the pitfalls
that were hit and solved. Read it before regenerating anything.

--------------------------------------------------------------------------------
## 1. What this project is
--------------------------------------------------------------------------------

A complete neural-TTS recitation of the **Mahābhārata Critical Edition** (BORI /
Sukthankar), all **18 parvans / 1,995 adhyāyas / ~232 hours**. Each chapter audio
file is framed with traditional recitation markers (bell + spoken chapter
announcement + verses + closing colophon + bell). Final products:

  - **Renamed marked WAVs** — `adhyaya_marked/mbh_PP_adh_AAA__<Subparva>__<slug>.wav`
  - **MP3 set** (96 kbps) — `adhyaya_mp3/…​.mp3`  (uploaded to archive.org)

--------------------------------------------------------------------------------
## 2. Compute environment (READ FIRST)
--------------------------------------------------------------------------------

All heavy work runs on a **RunPod pod** reached as compute target `ssh:runpod-a40`.

  - 4× NVIDIA A40 (46 GB each). System `python3` has torch 2.8+cu128, CUDA works.
  - **No conda on base**; a miniconda lives at `/workspace/miniconda3` with envs
    `py310` (render) and `audio` (ffmpeg, demucs, faster-whisper).
  - Home `/root` and the overlay `/` are **ephemeral** (wiped on container cycle,
    only ~30 GB). ALL durable state lives on **`/workspace`**, a MooseFS **network
    volume**.
  - **The RunPod network volume mounted at `/workspace` has a hard quota of 100 GB.**
    `df`/`statvfs` report the shared MooseFS *pool* (100+ TB) — IGNORE that; the real
    limit is 100 GB. Hardlinks and even directory entries count against the quota.
    (RESOLVED 2026-07-12: the network volume is named `convincing_harlequin_lark`,
    volume id `7w4yokjjfz`, datacenter **EU-SE-1**, since expanded to **250 GB**.
    It persists independently of any pod; attach a SECURE-cloud pod in EU-SE-1 to it.
    The A40×4 pod mentioned in older notes is long gone — any pod works for the CPU
    stages (splice/rename/mp3); GPU only matters for Stages A/B renders.)

### Submitting jobs (via host.compute in the repl tool)
```python
c = host.compute.create("ssh:runpod-a40",
                        provider_params={'scratch_root': '/workspace/operon_jobs'})
job = c.submit_job(command="...", intent="...", scheduler="none")   # scheduler='none' is REQUIRED
```

### Gotchas learned the hard way
  - **`scheduler='none'` is mandatory.** The pod's `scheduler: slurm` label is inert
    (no controller); without the override the daemon calls `sbatch` and fails.
  - **`conda activate` silently fails** in non-interactive job shells → use absolute
    paths: `/workspace/miniconda3/envs/py310/bin/python`,
    `/workspace/miniconda3/envs/audio/bin/{python,ffmpeg}`.
  - **`call_command` has a ~60 s timeout** and truncates long stdout with a `\u2026`
    ellipsis (~65 k). Use `submit_job` for anything that imports torch, and harvest
    large outputs as files, not via stdout.
  - **Long-running jobs must be launched detached**: `setsid nohup <cmd> >log 2>&1 </dev/null &`.
    A plain `submit_job` command hits the daemon's wall-clock ceiling (~105 min →
    exit 124) and the whole process tree is killed. Detached processes survive.
  - **Output harvest only collects files written into the job's own cwd.** To pull a
    result, `tar czf out.tgz -C <dir> files...` with the tar written into cwd and
    listed in `outputs=[...]`.
  - **The container CYCLES** between/within sessions (new hostname, sometimes new
    SSH IP/port). `/workspace` survives; in-flight jobs are lost. After a cycle the
    "SSH over exposed TCP" endpoint in the RunPod dashboard may change — update the
    compute target. Jupyter (HTTP proxy) can work even when direct-TCP SSH is wedged;
    from a Jupyter terminal, `service ssh restart` sometimes revives SSH.
  - **`ls glob` times out on MooseFS with many files** — use `find … | wc -l`.
    Huge `du -sh` can SIGPIPE (exit 141) when piped to `head`.

--------------------------------------------------------------------------------
## 3. Directory layout on the volume
--------------------------------------------------------------------------------
```
/workspace/
  vagdhenu/                 # the TTS model + render code (source, weights, BigVGAN)
    src/render.py           #   entrypoint: renders a clip shard -> wavs
    models/                 #   voice_steer_ema_*.pt, voice_armA_*.pt, voc_bigvgan_*.pth, vocab.txt
    src/reference_bank/     #   per-metre reference prosody (bank.json)
    BigVGAN/                #   must be on PYTHONPATH
  miniconda3/envs/{py310,audio}
  mbh_render/               # ALL pipeline state
    mbh_global_shard.json   #   77,888-clip verse work-list (seed 60, voice_steer/cfg3.0)
    mbh_drive.py            #   4-GPU verse render driver  [REMOTE-ONLY, see §7]
    mbh_supervisor.sh       #   self-healing loop for the render
    final_concat.py         #   concat per-clip wavs -> adhyaya/mbh_PP_adh_AAA.wav  [REMOTE-ONLY]
    wavs/                   #   77,889 per-clip wavs (verses/hemistichs/prose)
    adhyaya/                #   1,995 bare (unmarked) chapter wavs   ~36 GB
    adhyaya_marked/         #   1,995 MARKED + RENAMED chapter wavs  ~75 GB  ← primary WAV product
    adhyaya_mp3/            #   1,995 MP3s (96 kbps)                 ← archive.org upload
    markers/                #   marker render + splice workspace
      ann_shard_full.json   #     3,990-clip announcement work-list (1,995 open + 1,995 close)
      wavs/                 #     op_PP_AAA.wav / cl_PP_AAA.wav announcement clips
      bell_ref_short.wav    #     the intro/outro bell (SEE §6 provenance)
      manifest_named.tsv    #     old_filename <-> new_filename (the rename record)
```

--------------------------------------------------------------------------------
## 4. Pipeline stages (in order)
--------------------------------------------------------------------------------

**Stage A — Verse render** (already complete; scripts remote-only, see §7)
  - `mbh_supervisor.sh` → `mbh_drive.py` splits `mbh_global_shard.json` across 4 GPUs,
    runs one `render.py` per GPU into `wavs/`, then `final_concat.py` concatenates
    each complete adhyāya into `adhyaya/mbh_PP_adh_AAA.wav`.
  - Throughput ~10.7 s/clip/GPU → ~2.5–3 days for the full epic.

**Stage B — Marker announcements** (`scripts/markers/`)
  - `build_ann_shard.py` reads `data/mbh_marker_meta.json` (per-chapter Sanskrit
    ordinal colophons + per-parva header/closing-frame strings, with sandhi already
    applied) and the per-parva adhyaya counts, and emits the 3,990-clip
    `ann_shard_full.json` — one **opening** and one **closing** announcement per
    chapter. First-of-parva openings get the extra `śrīman-mahābhārate <parva>parva`
    header line.
    * Meter is **vasantatilaka**, `no_sandhi=True`, seed 60. (See §5 for WHY.)
  - `ann_drive.py` + `ann_supervisor.sh` render the shard across 4 GPUs into
    `markers/wavs/` as `op_PP_AAA.wav` / `cl_PP_AAA.wav`.

**Stage C — Splice** (`scripts/markers/splice_par.py` + `splice_par_launch.sh`)
  - For each chapter, assembles: `bell → opening → (0.35s) → bell → (0.45s) →
    verses → (0.6s) → closing → (0.35s) → bell`, with the announcement voice onset at
    **1.2 s** (bell tail overlaps under the voice), RMS-matched to the verse body,
    peak-normalised to 0.95, output to `adhyaya_marked/`.
  - `splice_par.py --mod 4 --rank R` shards the work; the launcher runs 4 workers.
    Single-process ≈0.25 files/s; 4-way ≈2.7 files/s (~10 min for all 1,995).

**Stage D — Rename** (`scripts/naming/`)
  - `build_filenames.py <align-repo> out.csv` regenerates the CE→title map from the
    shreevatsa/mahabharata-align-copy TSVs (see §8) → `mbh_adhyaya_filenames.csv`.
  - `do_rename_inplace.py` reads `rename_map.tsv` (old→new) and renames the WAVs
    **in place** inside `adhyaya_marked/` (zero extra bytes — do NOT hardlink into a
    second folder; the 100 GB quota can't hold a duplicate 75 GB set), writing
    `manifest_named.tsv`.
    * The bare originals remain in `adhyaya/` (un-marked, un-renamed) as a fallback,
      and the rename is fully reversible via the manifest.

**Stage E — MP3** (`scripts/mp3/`)
  - `mp3_enc.py --mod 4 --rank R` transcodes `adhyaya_marked/*.wav` →
    `adhyaya_mp3/*.mp3` at 96 kbps CBR, 24 kHz, via the `audio` env's ffmpeg
    (libmp3lame). `mp3_launch.sh` runs 4 workers. ffmpeg runs ~170× realtime; the
    whole set encodes in a few minutes (I/O-bound on the network volume). Full MP3
    set ≈ 8–10 GB.

--------------------------------------------------------------------------------
## 5. Why vasantatilaka + the "atha" problem (IMPORTANT design note)
--------------------------------------------------------------------------------

The opening announcement is a very short phrase ("atha prathamo'dhyāyaḥ"). Under the
**gadya (prose)** reference metre, the reference audio is long (~7.8 s), so a
2-syllable pada gets a tiny generation window and the light, unstressed **अथ (atha)
was dropped entirely** by the model. Verified by transcription (faster-whisper
large-v3, run in the `audio` env on the pod — HF weights are cached there; a local
transcription attempt failed because the model download is blocked by the sandbox).

Fixes tried: 3× repetition, prepending ॐ, sps/speed levers (some worked). **The clean
fix was switching the announcement metre to `vasantatilaka`**, single-pada form,
seed 60 — under which "atha" is reliably pronounced. Closings ("iti śrīman…") never
had the problem (the long stressed phrase after "iti" protects it). This is why
Stage B uses vasantatilaka, not gadya. If regenerating announcements, keep
vasantatilaka.

--------------------------------------------------------------------------------
## 6. Bell provenance (RIGHTS — resolve before any redistribution)
--------------------------------------------------------------------------------

**RESOLVED 2026-07-12.** The bell is now `assets/bell_ghanta_cc0.wav` — a real
ghanta strike, **CC0** (freesound.org/s/274316), processed to 1.45 s with a natural
damped decay (see `assets/BELL_PROVENANCE.md` and `scripts/bells/`). It was deployed
to the volume as `markers/bell_ref_short.wav` and Stages C+D+E were re-run in full
(see §10). The marked WAVs and MP3s are now fully redistributable (audio-rights-wise).

The ORIGINAL bell ("Kanda_1_BK-005-Ayodhya_Varnavam", extracted from a copyrighted
commercial recording, NOT cleared) is preserved as
`markers/bell_ref_short.ORIG_uncleared.wav` on the volume and in this repo's git
history — do not redistribute it or any audio embedding it (`adhyaya_mp3_OLD/`).

--------------------------------------------------------------------------------
## 7. What is NOT in this repo (remote-only)
--------------------------------------------------------------------------------

Almost everything was retrieved from the volume once SSH recovered and IS now in
this repo:

  - `vagdhenu/src/` — the full render code (render.py, render_core.py, G2P, meter,
    syllabify, normalize, prep_text, etc.) **plus the complete `reference_bank/`**
    (per-metre reference WAVs incl. `vasantatilaka.wav`, `gadya.wav`, `bank.json`).
  - `vagdhenu/{scripts,training,requirements.txt,README.md,LICENSE}`,
    `vagdhenu/models/vocab.txt`.
  - `scripts/render/{mbh_drive.py,mbh_supervisor.sh,final_concat.py}`.
  - `data/{mbh_global_shard.json (77,888 clips), ann_shard_full.json (3,990 clips),
    manifest_named.tsv}`.

**The ONLY thing still not in this repo is the ~3.1 GB of model WEIGHTS**, because
GitHub caps files at 100 MB. They live at `/workspace/vagdhenu/models/` on the pod:
  - `voice_steer_ema_2026-06-17.pt`  (1.35 GB)  ← primary voice used for the render
  - `voice_armA_ema_2026-06-11.pt`   (1.35 GB)
  - `voc_bigvgan_EMA_2026-06-11.pth` (450 MB)   ← BigVGAN vocoder
Also NOT included: the cloned `vagdhenu/BigVGAN/` vocoder repo (re-clonable) and the
HF caches (`vagdhenu/models/.cache`, `~/.cache/huggingface`).

To make the repo able to regenerate audio, add the 3 weights via **Git LFS** or ship
them as a separate release / cloud-storage bundle (NOT plain git). `vagdhenu` was
also re-provisionable via `/workspace/provision.sh` on the pod. Everything else
needed to drive the pipeline is present.

--------------------------------------------------------------------------------
## 8. Source of the chapter titles (naming data)
--------------------------------------------------------------------------------

Descriptive English titles + sub-parvan (upa-parvan) names come from
**https://github.com/shreevatsa/mahabharata-align-copy** — two TSVs that are
**positionally row-aligned** (2120 rows, verified):
  - `mappings/ce-ganguli/5-full.tsv` — `Skt_List` column: which CE adhyāyas each
    Ganguli section covers.
  - `mappings/Ganguli-Dutt.tsv` — `Section` (sub-parvan) + `Chapter name`
    (descriptive summary), from the public-domain Ganguli/Dutt translations.
Join on CE adhyāya via `Skt_List` (NOT on the Dutt chapter number — it does not line
up with CE numbering). This yields 100 % coverage of all 1,995 CE adhyāyas.
`scripts/naming/build_filenames.py` reproduces `data/mbh_adhyaya_filenames.csv`.

--------------------------------------------------------------------------------
## 9. Data corruption history (why integrity checks matter)
--------------------------------------------------------------------------------

The 100 GB quota filled up twice mid-run. When the volume is full, `final_concat.py`
writes **0-byte / truncated** adhyaya files silently. This produced:
  - `mbh_13_adh_001.wav` (one file), and later
  - **154 files** (133 in Parva 12, 21 in Parva 13) as 0-byte casualties.
All were repaired by re-running `final_concat.py` (it rebuilds any adhyāya whose
per-clip wavs are all present in `wavs/`), then re-splicing. **Always run an
integrity sweep** (open each file with soundfile; flag frames < 0.2 s) after any
concat, before declaring done. The final verified set: 1,995 files, 0 bad,
231.7 hours.

--------------------------------------------------------------------------------
## 10. Quick resume recipe
--------------------------------------------------------------------------------
```
# 1. reconnect
list_compute            # confirm ssh:runpod-a40 endpoint (may have changed after a cycle)
c = host.compute.create("ssh:runpod-a40", provider_params={'scratch_root':'/workspace/operon_jobs'})
c.call_command("echo alive; find /workspace/mbh_render/adhyaya_mp3 -name '*.mp3'|wc -l")

# 2. regenerate naming CSV (needs the align repo)
python scripts/naming/build_filenames.py mahabharata-align-copy data/mbh_adhyaya_filenames.csv

# 3. if re-belling: replace assets/bell_ref_short.wav, then on the pod re-run
#    splice_par_launch.sh  (Stage C) and mp3_launch.sh (Stage E) — both idempotent.
```

--------------------------------------------------------------------------------
## 10. 2026-07-12 re-splice run record (bell replacement)
--------------------------------------------------------------------------------

Executed by a Claude session from the production Mac; total compute ≈ $2.

  1. Attached a SECURE A5000 pod (EU-SE-1, $0.27/hr) to the network volume.
     Driven over RunPod's SSH proxy (`ssh -tt <podHostId>@ssh.runpod.io`; commands
     piped via stdin — the proxy ignores remote-command args and has no scp; bulk
     files move via `runpodctl send/receive`, base64-heredoc for small pushes).
  2. Backed up the old bell (`markers/bell_ref_short.ORIG_uncleared.wav`), installed
     the CC0 ghanta as `markers/bell_ref_short.wav`.
  3. Cleared `adhyaya_marked/`, parked the old MP3s as `adhyaya_mp3_OLD/`
     (deletion pending owner decision), verified 1,995 op_ + 1,995 cl_ announcement
     clips present.
  4. Ran `scripts/markers/run_all.sh` (splice → rename → mp3, absolute env paths,
     detached with setsid). Wall clock ~35 min. All stages logged in
     `markers/{splice_par_*,mp3_enc_*}.log` + `run_all.log`.
  5. Verified 1,995/1,995 MP3s name-exact against `rename_map.tsv`; pulled the set
     via runpodctl (10 GB, ~35 min). Copies: production Mac
     `~/mbharchive/mbh_mp3_newbell/` and Synology `Sanskrit AV/mahabharata tts/`.
  6. Terminated the pod. The volume retains: `wavs/` (77,889 verse clips),
     `adhyaya/` (bare concats), `adhyaya_marked/` (NEW-bell WAV masters, 75 GB),
     `adhyaya_mp3/` (NEW-bell MP3s), `adhyaya_mp3_OLD/` (UNCLEARED-bell MP3s).

Pitfall found this run: a first rebuild attempt used a naive bell→verses→bell
format from memory instead of reading this file — ALWAYS follow §4's stage list;
the announcements and colophons are integral to the product.
