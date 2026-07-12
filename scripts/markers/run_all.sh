#!/bin/bash
# One-shot chain: splice (4 workers) -> rename in place -> mp3 (4 workers).
# Uses ABSOLUTE env paths (conda activate silently fails in non-interactive shells).
# Launch detached:  setsid nohup bash run_all.sh > run_all.log 2>&1 < /dev/null &
cd /workspace/mbh_render/markers
PY=/workspace/miniconda3/envs/py310/bin/python
APY=/workspace/miniconda3/envs/audio/bin/python
for R in 0 1 2 3; do nohup $PY splice_par.py 4 $R > splice_par_$R.log 2>&1 < /dev/null & done
wait
echo SPLICE_ALL_DONE
$PY do_rename_inplace.py
for R in 0 1 2 3; do nohup $APY mp3_enc.py 4 $R > mp3_enc_$R.log 2>&1 < /dev/null & done
wait
echo CHAIN_ALL_DONE
