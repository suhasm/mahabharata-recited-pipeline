# Bell provenance — RESOLVED (2026-07-12)

`bell_ghanta_cc0.wav` is the intro/outro bell embedded in the current marked WAVs
and MP3s. It is fully cleared for redistribution:

- **Source**: "Ghanta-Leather-Mallet-2015-05-16" by the_very_Real_Horst,
  https://freesound.org/s/274316/ — **CC0** (public domain dedication). A real Hindu
  ghanta struck with a leather mallet.
- **Processing** (`scripts/bells/make_short_bell.py` + `extract_strikes.py`):
  mono 24 kHz, 35 Hz high-pass, the single most-isolated strike extracted
  (low-threshold peak detection so no neighboring strikes bleed in), exponential
  damp tau=0.45 s ("hand quieting the bell"), raised-cosine landing to silence at
  1.45 s, normalized.
- Deployed on the volume as `markers/bell_ref_short.wav` (the filename splice_par.py
  expects). The previous UNCLEARED bell (sampled from a commercial recording) is
  preserved on the volume as `markers/bell_ref_short.ORIG_uncleared.wav` and in this
  repo's git history — do not redistribute either; the working tree no longer
  contains it.
