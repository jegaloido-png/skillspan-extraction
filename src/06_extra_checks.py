"""Extra checks on the stored TEST predictions (no training, no GPU).

Usage: python src/06_extra_checks.py
Needs runs/final/*/test_pred.json and runs/dictionary/test_pred_{layer}_tuned.json.
Writes results/extra_checks.csv (long format: check, system, layer, key, value; BERT/JobBERT = mean over seeds).

Checks:
  gold_fate        boundary-only gold spans split by what overlaps them: only shorter predictions inside the gold span
                   ("inside"), a longer prediction that contains it ("contained"), or a mix/shift ("other")
  orphan_i         predicted spans that start with an I tag not preceded by B/I, and the exact F1 if such tags were set to O
  welch / bootstrap  JobBERT minus BERT-base exact F1: Welch t-test over the 5 seeds; 95% CI from resampling test sentences
  length_recall    exact recall of gold spans by length in tokens (1, 2, 3+)
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
spec = importlib.util.spec_from_file_location("load_data", SRC / "01_load_data.py")
dm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dm)
spec = importlib.util.spec_from_file_location("evaluate", SRC / "04_evaluate.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

SYSTEMS = ("dictionary", "bert", "jobbert")
rows = []


def add(check, system, layer, key, value):
    rows.append({"check": check, "system": system, "layer": layer, "key": key, "value": value})


def load_tags(system, layer):
    """list over seeds of list over sentences of tag lists."""
    if system == "dictionary":
        return [json.loads((ROOT / "runs" / "dictionary" / f"test_pred_{layer}_tuned.json").read_text(encoding="utf-8"))]
    files = sorted((ROOT / "runs" / "final").glob(f"{system}_{layer}_lr*_seed*/test_pred.json"))
    assert len(files) == 5, (system, layer, len(files))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def orphan_to_o(tags):
    """Set to O every I tag that does not continue a span (strict BIO reading)."""
    out, prev = [], "O"
    for t in tags:
        if t.startswith("I") and prev == "O":
            out.append("O")
            prev = "O"
        else:
            out.append(t)
            prev = t
    return out


def overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def sentence_counts(gold, pred):
    """tp, n_pred, n_gold for one sentence (exact match)."""
    return len(set(gold) & set(pred)), len(pred), len(gold)


def f1(tp, npred, ngold):
    p, r = tp / npred if npred else 0.0, tp / ngold if ngold else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


test = dm.load_split("test")
train_sents = {tuple(r["tokens"]) for r in dm.load_split("train")}
dup = np.array([tuple(r["tokens"]) in train_sents for r in test])
add("duplicates", "-", "all", "share_test_sentences_in_train", float(dup.mean()))
rng = np.random.default_rng(0)

for layer, key in dm.TAG_KEYS.items():
    gold = [dm.bio_to_spans(r[key]) for r in test]
    add("duplicates", "-", layer, "share_gold_spans_in_duplicates",
        sum(len(g) for g, d in zip(gold, dup) if d) / sum(len(g) for g in gold))
    # trivial predictor: the whole sentence as one span, in every sentence (partial-match sanity check)
    whole = [[(0, len(r["tokens"]))] for r in test]
    tr = ev.evaluate_spans(gold, whole)
    add("whole_sentence_baseline", "-", layer, "partial_f1", tr["partial_f1"])
    add("whole_sentence_baseline", "-", layer, "exact_f1", tr["exact_f1"])
    counts = {}  # system -> array (seeds, sentences, 3)
    for system in SYSTEMS:
        runs_tags = load_tags(system, layer)
        fate = {"inside": [], "contained": [], "other": [], "missed": [], "exact": []}
        orphan_n, orphan_f1, base_f1 = [], [], []
        len_found = {k: [] for k in ("1", "2", "3+")}
        len_gold = {k: 0 for k in ("1", "2", "3+")}
        arr = []
        for tags in runs_tags:
            pred = [dm.bio_to_spans(t) for t in tags]
            # ---- gold fate
            c = {k: 0 for k in fate}
            lf = {k: 0 for k in len_found}
            for g_s, p_s in zip(gold, pred):
                for g in g_s:
                    lk = "1" if g[1] - g[0] == 1 else "2" if g[1] - g[0] == 2 else "3+"
                    if g in p_s:
                        c["exact"] += 1
                        lf[lk] += 1
                        continue
                    ov = [p for p in p_s if overlap(p, g)]
                    if not ov:
                        c["missed"] += 1
                    elif all(g[0] <= p[0] and p[1] <= g[1] for p in ov):
                        c["inside"] += 1
                    elif any(p[0] <= g[0] and g[1] <= p[1] for p in ov):
                        c["contained"] += 1
                    else:
                        c["other"] += 1
            for k in fate:
                fate[k].append(c[k])
            for k in len_found:
                len_found[k].append(lf[k])
            for g_s in gold:
                pass
            # ---- orphan I
            n_orph = sum(dm.check_bio(t) for t in tags)
            orphan_n.append(n_orph)
            strict = [dm.bio_to_spans(orphan_to_o(t)) for t in tags]
            base_f1.append(ev.evaluate_spans(gold, pred)["exact_f1"])
            orphan_f1.append(ev.evaluate_spans(gold, strict)["exact_f1"])
            arr.append([sentence_counts(g_s, p_s) for g_s, p_s in zip(gold, pred)])
        for g_s in gold:
            for g in g_s:
                len_gold["1" if g[1] - g[0] == 1 else "2" if g[1] - g[0] == 2 else "3+"] += 1
        for k, v in fate.items():
            add("gold_fate", system, layer, k, float(np.mean(v)))
        add("orphan_i", system, layer, "orphan_tags", float(np.mean(orphan_n)))
        add("orphan_i", system, layer, "exact_f1_lenient", float(np.mean(base_f1)))
        add("orphan_i", system, layer, "exact_f1_strict", float(np.mean(orphan_f1)))
        for k in len_found:
            add("length_recall", system, layer, f"n_gold_{k}", len_gold[k])
            add("length_recall", system, layer, f"recall_{k}", float(np.mean(len_found[k])) / len_gold[k])
        counts[system] = np.array(arr, dtype=float)  # seeds x sentences x 3
        nd = ~dup
        add("duplicates", system, layer, "exact_f1_without_duplicates",
            float(np.mean([f1(*s[nd].sum(axis=0)) for s in counts[system]])))
        if system != "dictionary":
            add("seed_std", system, layer, "exact_f1_std", float(np.std(base_f1, ddof=1)))

    # ---- JobBERT minus BERT-base
    jb, bb = counts["jobbert"], counts["bert"]
    f_j = [f1(*s.sum(axis=0)) for s in jb]
    f_b = [f1(*s.sum(axis=0)) for s in bb]
    t, p = stats.ttest_ind(f_j, f_b, equal_var=False)
    add("welch", "jobbert-bert", layer, "diff", float(np.mean(f_j) - np.mean(f_b)))
    add("welch", "jobbert-bert", layer, "p", float(p))
    n = len(test)
    diffs, diffs_dict = [], []
    dic = counts["dictionary"][0]
    for _ in range(1000):
        idx = rng.integers(0, n, n)
        dj = np.mean([f1(*s[idx].sum(axis=0)) for s in jb])
        db = np.mean([f1(*s[idx].sum(axis=0)) for s in bb])
        dd = f1(*dic[idx].sum(axis=0))
        diffs.append(dj - db)
        diffs_dict.append(dj - dd)
    for name, d in (("jobbert-bert", diffs), ("jobbert-dictionary", diffs_dict)):
        add("bootstrap", name, layer, "ci_low", float(np.percentile(d, 2.5)))
        add("bootstrap", name, layer, "ci_high", float(np.percentile(d, 97.5)))

out = pd.DataFrame(rows)
out.round(5).to_csv(ROOT / "results" / "extra_checks.csv", index=False)
print(out.round(4).to_string(index=False))
