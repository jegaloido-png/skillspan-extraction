#!/usr/bin/env bash
# Extra dev probe at lr 7e-5 (the best lr of the 2e-5/3e-5/5e-5 grid was often 5e-5, i.e. at the grid edge).
# One stream per model so two streams can share a GPU. Test set is never touched.
# Usage (project root): PY=/root/venv/bin/python bash src/run_lr_probe.sh bert   # and: ... jobbert
set -u
PY="${PY:-python}"
MODEL="$1"
for layer in skill knowledge; do
  "$PY" src/03_train_bert.py --model "$MODEL" --layer "$layer" --lr 7e-5 --seed 3477689 \
    --out_dir runs/lr_search 2>&1 | grep -E "done|skip|Error|Traceback"
done
echo "ALL_DONE_$MODEL"
