"""Span-level metrics shared by all systems (dictionary and BERT), plus the test-set report.

Usage: python src/04_evaluate.py
Reads runs/final/*/metrics.json (BERT test scores computed by 03_train_bert.py with
--predict_test) and results/dictionary_test.csv, and writes:
  results/test_results_per_run.csv   one row per run and source
  results/test_results_summary.csv   mean and std (sample std, ddof=1) over seeds
  results/test_results_summary.md    main comparison table (all sources) in Markdown

Spans are (start, end_exclusive) token offsets inside one sentence.
Exact match : a predicted span is correct only if (start, end) equals a gold span.
Partial     : a predicted span is correct if it overlaps >= 1 gold span;
              a gold span is found if it overlaps >= 1 predicted span.
              (precision and recall are computed on these two relaxed notions)
"""


def _prf(tp_p, n_pred, tp_r, n_gold):
    p = tp_p / n_pred if n_pred else 0.0
    r = tp_r / n_gold if n_gold else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def _overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def evaluate_spans(gold, pred):
    """gold, pred: lists (one entry per sentence) of lists of (start, end) spans."""
    assert len(gold) == len(pred)
    n_gold = n_pred = tp_exact = p_part = r_part = 0
    for g, p in zip(gold, pred):
        g, p = list(g), list(p)
        n_gold += len(g)
        n_pred += len(p)
        gs = set(g)
        tp_exact += sum(1 for s in set(p) if s in gs)
        p_part += sum(1 for s in p if any(_overlap(s, x) for x in g))
        r_part += sum(1 for x in g if any(_overlap(x, s) for s in p))
    pe, re_, fe = _prf(tp_exact, n_pred, tp_exact, n_gold)
    pp, rp, fp = _prf(p_part, n_pred, r_part, n_gold)
    return {
        "n_gold": n_gold, "n_pred": n_pred, "tp_exact": tp_exact,
        "exact_p": pe, "exact_r": re_, "exact_f1": fe,
        "partial_p": pp, "partial_r": rp, "partial_f1": fp,
    }


def main():
    import json
    from pathlib import Path

    import pandas as pd

    root = Path(__file__).resolve().parent.parent
    rows = []
    for p in sorted((root / "runs" / "final").glob("*/metrics.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        c = m["config"]
        for source, s in m["test"].items():
            rows.append({"system": c["model"], "layer": c["layer"], "seed": c["seed"], "lr": c["lr"],
                         "best_epoch": m["best_epoch"], "source": source, **s})
    per_run = pd.DataFrame(rows)
    per_run.to_csv(root / "results" / "test_results_per_run.csv", index=False)

    metrics = ["exact_p", "exact_r", "exact_f1", "partial_p", "partial_r", "partial_f1"]
    agg = per_run.groupby(["system", "layer", "source"])[metrics].agg(["mean", "std"])
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    agg["n_seeds"] = per_run.groupby(["system", "layer", "source"]).size()
    agg = agg.reset_index()

    dic = pd.read_csv(root / "results" / "dictionary_test.csv").rename(columns={"system": "system_full"})
    dic["system"] = dic["system_full"]
    for mname in metrics:
        dic[f"{mname}_mean"], dic[f"{mname}_std"] = dic[mname], float("nan")
    dic["n_seeds"] = 1
    keep = ["system", "layer", "source", "n_seeds"] + [f"{m}_{k}" for m in metrics for k in ("mean", "std")]
    summary = pd.concat([agg[keep], dic[keep]], ignore_index=True)
    summary.round(4).to_csv(root / "results" / "test_results_summary.csv", index=False)

    def fmt(r, m):
        return f"{r[m + '_mean']:.3f}" + (f" ± {r[m + '_std']:.3f}" if r["n_seeds"] > 1 else "")

    order = ["dictionary_pure", "dictionary_tuned", "bert", "jobbert"]
    lines = []
    for layer in ("skill", "knowledge"):
        lines.append(f"### {layer.capitalize()} (test, all sources)\n")
        lines.append("| system | seeds | exact P | exact R | exact F1 | partial P | partial R | partial F1 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        sub = summary[(summary.layer == layer) & (summary.source == "all")].set_index("system")
        for s in order:
            if s in sub.index:
                r = sub.loc[s]
                lines.append(f"| {s} | {int(r.n_seeds)} | " + " | ".join(fmt(r, m) for m in metrics) + " |")
        lines.append("")
    (root / "results" / "test_results_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
