#!/usr/bin/env bash
# Learning-rate search on DEV: 3 lrs x 2 models x 2 layers, one seed. Test set is never touched.
# Resumable: 03_train_bert.py skips runs whose metrics.json already exists.
# Usage (from project root): PY=/root/venv/bin/python bash src/run_lr_search.sh
set -u
PY="${PY:-python}"
SEED=3477689
for lr in 2e-5 3e-5 5e-5; do
  for model in bert jobbert; do
    for layer in skill knowledge; do
      "$PY" src/03_train_bert.py --model "$model" --layer "$layer" --lr "$lr" --seed "$SEED" \
        --out_dir runs/lr_search 2>&1 | grep -E "^\{|done|skip|Error|Traceback"
    done
  done
done
echo ALL_DONE
