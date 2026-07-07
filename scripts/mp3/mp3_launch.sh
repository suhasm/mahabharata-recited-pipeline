#!/bin/bash
cd /workspace/mbh_render/markers
for R in 0 1 2 3; do
  nohup /workspace/miniconda3/envs/audio/bin/python mp3_enc.py 4 $R > mp3_enc_$R.log 2>&1 < /dev/null &
done
wait
echo "MP3 ALL DONE" > mp3_done.flag
cat mp3_enc_*.log | grep DONE
