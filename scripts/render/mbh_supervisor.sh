#!/bin/bash
# Self-healing supervisor: re-runs the driver until all clips are done.
source /workspace/miniconda3/etc/profile.d/conda.sh; conda activate py310
cd /workspace/mbh_render
echo $$ > supervisor.lock            # claim the lock with our own PID
trap 'rm -f supervisor.lock' EXIT
echo "[sup] START $(date) pid=$$" >> supervisor.log
for i in $(seq 1 500); do
  python mbh_drive.py >> supervisor.log 2>&1
  rc=$?
  echo "[sup] pass $i rc=$rc $(date)" >> supervisor.log
  if [ $rc -eq 0 ]; then echo "[sup] ALL DONE $(date)" >> supervisor.log; break; fi
  sleep 20
done
