#!/usr/bin/env bash
# Final runs: {bert, jobbert} x {skill, knowledge} x 5 seeds, lr chosen on dev, test predicted
# with the best-dev epoch (--predict_test). Two streams (one per model) can run in parallel on one GPU.
# Resumable: finished runs (metrics.json present) are skipped by 03_train_bert.py.
# Usage (project root): PY=/root/venv/bin/python bash src/run_final.sh bert    # and: ... jobbert
set -u
PY="${PY:-python}"
MODEL="$1"
LR=5e-5
for seed in 3477689 4213916 8749520 6828303 9364029; do
  for layer in skill knowledge; do
    "$PY" src/03_train_bert.py --model "$MODEL" --layer "$layer" --lr "$LR" --seed "$seed" \
      --epochs 10 --predict_test --out_dir runs/final 2>&1 | grep -E "done|skip|Error|Traceback"
  done
done
echo "ALL_DONE_$MODEL"
