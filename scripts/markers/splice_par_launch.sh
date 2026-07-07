#!/bin/bash
cd /workspace/mbh_render/markers
source /workspace/miniconda3/etc/profile.d/conda.sh && conda activate py310
# kill any existing single splicer
pkill -f "splice.py" 2>/dev/null; sleep 1
for R in 0 1 2 3; do
  nohup python splice_par.py 4 $R > splice_par_$R.log 2>&1 < /dev/null &
done
wait
echo "ALL SPLICE WORKERS DONE" > splice_par_done.flag
cat splice_par_*.log
