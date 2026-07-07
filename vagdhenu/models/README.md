# Model weights (NOT in git)

`vocab.txt` (the tokenizer vocab, resolved by render.py) IS included here.

The three model weights are too large for GitHub (100 MB/file limit) and are
excluded via .gitignore (*.pt, *.pth). Obtain them from the compute volume at
`/workspace/vagdhenu/models/` and place them here, or ship via Git LFS / a release:

  - voice_steer_ema_2026-06-17.pt   (~1.35 GB)  ← primary voice used for the render
  - voice_armA_ema_2026-06-11.pt    (~1.35 GB)
  - voc_bigvgan_EMA_2026-06-11.pth  (~450 MB)   ← BigVGAN vocoder
