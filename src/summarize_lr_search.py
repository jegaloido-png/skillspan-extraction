"""Collect the dev metrics of the learning-rate search into results/lr_search_dev.csv (+ .md).

Usage: python src/summarize_lr_search.py
Reads runs/lr_search/*/metrics.json. No test data is involved.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
rows = []
for p in sorted((ROOT / "runs" / "lr_search").glob("*/metrics.json")):
    m = json.loads(p.read_text(encoding="utf-8"))
    c, d = m["config"], m["dev"]["all"]
    rows.append({
        "model": c["model"], "layer": c["layer"], "lr": c["lr"], "seed": c["seed"],
        "best_epoch": m["best_epoch"], "epochs_run": len(m["history"]),
        "dev_exact_p": d["exact_p"], "dev_exact_r": d["exact_r"], "dev_exact_f1": d["exact_f1"],
        "dev_partial_f1": d["partial_f1"], "seconds": m["seconds"], "device": m["device"],
    })
df = pd.DataFrame(rows).sort_values(["layer", "model", "lr"])
metric_cols = [c for c in df.columns if c.startswith("dev_")]
df[metric_cols] = df[metric_cols].round(4)
df["lr"] = df["lr"].map(lambda v: f"{v:g}")  # keep 2e-05 readable (round() would turn it into 0.0)
df.to_csv(ROOT / "results" / "lr_search_dev.csv", index=False)
(ROOT / "results" / "lr_search_dev.md").write_text(df.to_markdown(index=False), encoding="utf-8")
print(df.to_string(index=False))
best = df.loc[df.groupby(["layer", "model"])["dev_exact_f1"].idxmax()]
print("\nBest lr per (layer, model) by dev exact F1:")
print(best[["layer", "model", "lr", "dev_exact_f1", "best_epoch"]].to_string(index=False))
