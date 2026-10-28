"""Error analysis on the TEST predictions (dictionary vs BERT-base vs JobBERT).

Usage: python src/05_error_analysis.py
Needs runs/final/*/test_pred.json (from 03_train_bert.py --predict_test) and
runs/dictionary/test_pred_{layer}_tuned.json (from 02_dictionary_baseline.py --test).

Outputs in results/:
  error_taxonomy.csv / .md   what happens to predicted and gold spans (boundary errors, spurious, missed)
  recall_seen_unseen.csv     exact recall on gold expressions seen / not seen in the training annotations
  error_examples.md          gold vs predictions side by side for 24 sentences (seed 3477689 for BERT/JobBERT)
"""
import importlib.util
import json
import random
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
spec = importlib.util.spec_from_file_location("load_data", SRC / "01_load_data.py")
data_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_mod)
load_split, bio_to_spans, TAG_KEYS = data_mod.load_split, data_mod.bio_to_spans, data_mod.TAG_KEYS

EXAMPLE_SEED = 3477689
SYSTEMS = ("dictionary", "bert", "jobbert")


def load_preds():
    """preds[system][layer] = list over seeds of list (per sentence) of span lists."""
    preds = {s: {} for s in SYSTEMS}
    for layer in TAG_KEYS:
        d = json.loads((ROOT / "runs" / "dictionary" / f"test_pred_{layer}_tuned.json").read_text(encoding="utf-8"))
        preds["dictionary"][layer] = {"-": [bio_to_spans(t) for t in d]}
        for model in ("bert", "jobbert"):
            preds[model][layer] = {}
            for f in sorted((ROOT / "runs" / "final").glob(f"{model}_{layer}_lr*_seed*/test_pred.json")):
                seed = int(f.parent.name.split("_seed")[1])
                preds[model][layer][seed] = [bio_to_spans(t) for t in json.loads(f.read_text(encoding="utf-8"))]
    return preds


def overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def classify_sentence(gold, pred):
    """Return dict of lists: pred_exact, shorter (pred inside a gold span), longer, shifted, spurious, missed."""
    out = {k: [] for k in ("pred_exact", "shorter", "longer", "shifted", "spurious", "missed", "gold_boundary_only")}
    gs = set(gold)
    for p in pred:
        if p in gs:
            out["pred_exact"].append(p)
            continue
        ov = [g for g in gold if overlap(p, g)]
        if not ov:
            out["spurious"].append(p)
        elif any(g[0] <= p[0] and p[1] <= g[1] for g in ov):
            out["shorter"].append(p)
        elif any(p[0] <= g[0] and g[1] <= p[1] for g in ov):
            out["longer"].append(p)
        else:
            out["shifted"].append(p)
    ps = set(pred)
    for g in gold:
        if g in ps:
            continue
        (out["gold_boundary_only"] if any(overlap(g, p) for p in pred) else out["missed"]).append(g)
    return out


def render(tokens, spans):
    out = list(tokens)
    for s, e in sorted(spans, reverse=True):
        out[s] = "[" + out[s]
        out[e - 1] = out[e - 1] + "]"
    return " ".join(out)


def main():
    test = load_split("test")
    train = load_split("train")
    preds = load_preds()
    seeds_bert = sorted(preds["bert"]["skill"])
    tax_rows, seen_rows = [], []

    for layer, key in TAG_KEYS.items():
        gold_all = [bio_to_spans(r[key]) for r in test]
        train_expr = {tuple(t.lower() for t in r["tokens"][s:e]) for r in train for s, e in bio_to_spans(r[key])}
        for system in SYSTEMS:
            for source in ("all", "house", "tech"):
                idx = [i for i, r in enumerate(test) if source == "all" or r["source"] == source]
                per_seed = []
                for seed, sp in preds[system][layer].items():
                    c = {k: 0 for k in ("n_gold", "n_pred", "pred_exact", "shorter", "longer", "shifted", "spurious",
                                        "missed", "gold_boundary_only", "seen_gold", "seen_found", "unseen_gold", "unseen_found")}
                    for i in idx:
                        r = test[i]
                        cl = classify_sentence(gold_all[i], sp[i])
                        c["n_gold"] += len(gold_all[i])
                        c["n_pred"] += len(sp[i])
                        for k in ("pred_exact", "shorter", "longer", "shifted", "spurious", "missed", "gold_boundary_only"):
                            c[k] += len(cl[k])
                        found = set(cl["pred_exact"])
                        for g in gold_all[i]:
                            seen = tuple(t.lower() for t in r["tokens"][g[0]:g[1]]) in train_expr
                            c["seen_gold" if seen else "unseen_gold"] += 1
                            c["seen_found" if seen else "unseen_found"] += int(g in found)
                    per_seed.append(c)
                mean = {k: sum(c[k] for c in per_seed) / len(per_seed) for k in per_seed[0]}
                tax_rows.append({"system": system, "layer": layer, "source": source, "n_seeds": len(per_seed), **mean})
                if source == "all":
                    seen_rows.append({
                        "system": system, "layer": layer, "n_seeds": len(per_seed),
                        "seen_gold": mean["seen_gold"], "seen_exact_recall": mean["seen_found"] / mean["seen_gold"],
                        "unseen_gold": mean["unseen_gold"], "unseen_exact_recall": mean["unseen_found"] / mean["unseen_gold"]})

    tax = pd.DataFrame(tax_rows)
    tax.drop(columns=["seen_gold", "seen_found", "unseen_gold", "unseen_found"]).round(2).to_csv(
        ROOT / "results" / "error_taxonomy.csv", index=False)
    pd.DataFrame(seen_rows).round(4).to_csv(ROOT / "results" / "recall_seen_unseen.csv", index=False)

    lines = ["Error taxonomy on test (mean over seeds for BERT/JobBERT). Predicted spans are split into exact, boundary errors "
             "(`shorter` = prediction inside a gold span, `longer` = prediction contains a gold span, `shifted` = partial overlap) "
             "and `spurious` (no overlap). Gold spans: `missed` (no overlapping prediction) or `gold_boundary_only` (overlapped but never exact).\n"]
    for layer in TAG_KEYS:
        lines.append(f"### {layer.capitalize()} (all sources)\n")
        lines.append("| system | gold | pred | exact | shorter | longer | shifted | spurious | gold missed | gold boundary-only |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in tax[(tax.layer == layer) & (tax.source == "all")].iterrows():
            lines.append(f"| {r.system} | {r.n_gold:.0f} | {r.n_pred:.0f} | {r.pred_exact:.0f} | {r.shorter:.0f} | {r.longer:.0f} | "
                         f"{r.shifted:.0f} | {r.spurious:.0f} | {r.missed:.0f} | {r.gold_boundary_only:.0f} |")
        lines.append("")
    (ROOT / "results" / "error_taxonomy.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- examples (BERT/JobBERT: seed EXAMPLE_SEED) ----
    rng = random.Random(0)
    ex_lines = [f"# Gold vs predictions on test (24 examples)\n\nBERT/JobBERT predictions are from seed {EXAMPLE_SEED}. "
                "Spans are in square brackets. Selection is deterministic (random.Random(0)) among sentences of at most 30 tokens.\n"]
    cats = [
        ("Dictionary: boundary error", lambda d, b, j, g: bool(classify_sentence(g, d)["shorter"] + classify_sentence(g, d)["longer"] + classify_sentence(g, d)["shifted"])),
        ("Dictionary misses, BERT finds it exactly", lambda d, b, j, g: any(x in set(b) for x in classify_sentence(g, d)["missed"])),
        ("BERT: boundary error", lambda d, b, j, g: bool(classify_sentence(g, b)["shorter"] + classify_sentence(g, b)["longer"] + classify_sentence(g, b)["shifted"])),
        ("BERT: spurious prediction", lambda d, b, j, g: bool(classify_sentence(g, b)["spurious"])),
        ("JobBERT exact, BERT wrong", lambda d, b, j, g: any(x in set(j) and x not in set(b) for x in g)),
        ("BERT exact, JobBERT wrong", lambda d, b, j, g: any(x in set(b) and x not in set(j) for x in g)),
    ]
    n = 0
    for layer, key in TAG_KEYS.items():
        gold_all = [bio_to_spans(r[key]) for r in test]
        d_sp, b_sp, j_sp = (preds["dictionary"][layer]["-"], preds["bert"][layer][EXAMPLE_SEED], preds["jobbert"][layer][EXAMPLE_SEED])
        used = set()
        for name, cond in cats:
            cands = [i for i, r in enumerate(test) if len(r["tokens"]) <= 30 and i not in used and gold_all[i]
                     and cond(d_sp[i], b_sp[i], j_sp[i], gold_all[i])]
            for i in rng.sample(cands, min(2, len(cands))):
                used.add(i)
                n += 1
                r = test[i]
                ex_lines += [f"## {n}. {layer.capitalize()} – {name} (source: {r['source']}, idx {r['idx']})\n",
                             f"- GOLD:     {render(r['tokens'], gold_all[i])}",
                             f"- DICT:     {render(r['tokens'], d_sp[i])}",
                             f"- BERT:     {render(r['tokens'], b_sp[i])}",
                             f"- JOBBERT:  {render(r['tokens'], j_sp[i])}\n"]
    (ROOT / "results" / "error_examples.md").write_text("\n".join(ex_lines), encoding="utf-8")
    print(f"examples written: {n}")
    print("\n".join(lines))
    print(pd.DataFrame(seen_rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
