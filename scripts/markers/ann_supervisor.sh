#!/bin/bash
cd /workspace/mbh_render/markers
source /workspace/miniconda3/etc/profile.d/conda.sh && conda activate py310
for i in $(seq 1 50); do
  python /workspace/mbh_render/markers/ann_drive.py >> ann_sup.log 2>&1
  rc=$?
  echo "[$(date -u)] driver pass rc=$rc" >> ann_sup.log
  if [ $rc -eq 0 ]; then echo "DONE" >> ann_sup.log; break; fi
  sleep 3
done
