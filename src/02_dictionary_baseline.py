"""Dictionary baseline: expressions collected from the TRAIN set only, longest match.

Usage: python src/02_dictionary_baseline.py
Tunes two knobs on DEV (never on test):
  - case handling: cased vs lowercased matching
  - min_precision: keep an expression only if, in the training text, it is
    annotated at least this often (drops ambiguous words such as "work").
Writes results/dictionary_dev.csv, results/dictionary_dev_by_source.csv,
runs/dictionary/*.json (chosen dictionaries) and runs/dictionary_dev_meta.json.
"""
import importlib.util
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


data_mod = _load("load_data", "01_load_data.py")
eval_mod = _load("evaluate", "04_evaluate.py")
load_split, bio_to_spans, TAG_KEYS = data_mod.load_split, data_mod.bio_to_spans, data_mod.TAG_KEYS
evaluate_spans = eval_mod.evaluate_spans

CASES = ("cased", "lower")
THRESHOLDS = (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8)


def norm(tokens, case):
    return tuple(t.lower() for t in tokens) if case == "lower" else tuple(tokens)


def build_dictionary(train_rows, layer, case, min_precision):
    """Map expression (tuple of tokens) -> annotation precision in train.

    Takes ONLY train rows by design: the test set never reaches this function.
    precision = (#times annotated as a span) / (#times the token sequence occurs).
    """
    key = TAG_KEYS[layer]
    annotated = Counter()
    for r in train_rows:
        for s, e in bio_to_spans(r[key]):
            annotated[norm(r["tokens"][s:e], case)] += 1
    lengths = sorted({len(k) for k in annotated})
    occurrences = Counter()
    for r in train_rows:
        toks = norm(r["tokens"], case)
        for n in lengths:
            for i in range(len(toks) - n + 1):
                g = toks[i:i + n]
                if g in annotated:
                    occurrences[g] += 1
    prec = {k: annotated[k] / occurrences[k] for k in annotated}
    return {k: v for k, v in prec.items() if v >= min_precision}


def predict(rows, dictionary, case):
    """Left-to-right longest match on token sequences; non-overlapping spans."""
    max_len = max((len(k) for k in dictionary), default=0)
    out = []
    for r in rows:
        toks = norm(r["tokens"], case)
        spans, i = [], 0
        while i < len(toks):
            for n in range(min(max_len, len(toks) - i), 0, -1):
                if toks[i:i + n] in dictionary:
                    spans.append((i, i + n))
                    i += n
                    break
            else:
                i += 1
        out.append(spans)
    return out


def check_no_test_leak(train_rows, test_rows, layer, case, dictionary):
    """Automatic check: no expression that appears ONLY in the test set is in the dictionary.

    (Expressions that also occur in train are legitimately in the dictionary:
    they come from the training annotations, not from the test set.)
    """
    key = TAG_KEYS[layer]
    train_expr = {norm(r["tokens"][s:e], case) for r in train_rows for s, e in bio_to_spans(r[key])}
    test_expr = {norm(r["tokens"][s:e], case) for r in test_rows for s, e in bio_to_spans(r[key])}
    test_only = test_expr - train_expr
    leaked = test_only & set(dictionary)
    assert not leaked, f"{len(leaked)} test-only expressions in dictionary, e.g. {list(leaked)[:3]}"
    assert set(dictionary) <= train_expr, "dictionary contains expressions not annotated in train"
    return len(test_only), len(test_expr)


def main():
    t0 = time.time()
    train, dev, test = (load_split(s) for s in ("train", "dev", "test"))
    grid, best = [], {}
    for layer, key in TAG_KEYS.items():
        gold = [bio_to_spans(r[key]) for r in dev]
        for case in CASES:
            for th in THRESHOLDS:
                d = build_dictionary(train, layer, case, th)
                check_no_test_leak(train, test, layer, case, d)
                m = evaluate_spans(gold, predict(dev, d, case))
                row = {"layer": layer, "case": case, "min_precision": th, "dict_size": len(d), **m}
                grid.append(row)
                if layer not in best or m["exact_f1"] > best[layer]["exact_f1"]:
                    best[layer] = row
    df = pd.DataFrame(grid)
    (ROOT / "results").mkdir(exist_ok=True)
    df.round(4).to_csv(ROOT / "results" / "dictionary_dev.csv", index=False)

    (ROOT / "runs" / "dictionary").mkdir(parents=True, exist_ok=True)
    by_source = []
    for layer, b in best.items():
        key = TAG_KEYS[layer]
        d = build_dictionary(train, layer, b["case"], b["min_precision"])
        n_testonly, n_testexpr = check_no_test_leak(train, test, layer, b["case"], d)
        (ROOT / "runs" / "dictionary" / f"{layer}.json").write_text(
            json.dumps({" ".join(k): round(v, 4) for k, v in sorted(d.items())}, ensure_ascii=False, indent=0), encoding="utf-8")
        for source in ("house", "tech", "all"):
            rows = [r for r in dev if source == "all" or r["source"] == source]
            gold = [bio_to_spans(r[key]) for r in rows]
            m = evaluate_spans(gold, predict(rows, d, b["case"]))
            by_source.append({"layer": layer, "source": source, "case": b["case"], "min_precision": b["min_precision"],
                              "dict_size": len(d), **m})
        print(f"[{layer}] chosen case={b['case']} min_precision={b['min_precision']} dict_size={len(d)}; "
              f"test-only expressions (absent from dict): {n_testonly}/{n_testexpr}")
    out = pd.DataFrame(by_source).round(4)
    out.to_csv(ROOT / "results" / "dictionary_dev_by_source.csv", index=False)
    print(out[["layer", "source", "dict_size", "n_gold", "n_pred", "exact_p", "exact_r", "exact_f1",
               "partial_p", "partial_r", "partial_f1"]].to_string(index=False))

    meta = {"command": "python src/02_dictionary_baseline.py", "python": platform.python_version(),
            "pandas": pd.__version__, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seconds": round(time.time() - t0, 1), "selection": "dev exact F1", "seed": "none (deterministic)"}
    (ROOT / "runs" / "dictionary_dev_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


def spans_to_tags(n_tokens, spans):
    tags = ["O"] * n_tokens
    for s, e in spans:
        tags[s] = "B"
        for i in range(s + 1, e):
            tags[i] = "I"
    return tags


def test_main():
    """FINAL evaluation on TEST with the settings already chosen on dev (read from the dev grid).

    Two versions per layer: 'tuned' (best dev F1) and 'pure' (min_precision 0, best case on dev).
    Saves word-level BIO predictions in the same format as the BERT runs, for the error analysis.
    """
    t0 = time.time()
    train, test = load_split("train"), load_split("test")
    grid = pd.read_csv(ROOT / "results" / "dictionary_dev.csv")
    out_dir = ROOT / "runs" / "dictionary"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for layer, key in TAG_KEYS.items():
        g = grid[grid.layer == layer]
        pure_g = g[g.min_precision == 0]
        for version, sel in (("tuned", g.loc[g.exact_f1.idxmax()]), ("pure", pure_g.loc[pure_g.exact_f1.idxmax()])):
            case, th = sel["case"], float(sel["min_precision"])
            d = build_dictionary(train, layer, case, th)
            check_no_test_leak(train, test, layer, case, d)
            pred = predict(test, d, case)
            (out_dir / f"test_pred_{layer}_{version}.json").write_text(
                json.dumps([spans_to_tags(len(r["tokens"]), p) for r, p in zip(test, pred)]), encoding="utf-8")
            for source in ("all", "house", "tech"):
                idx = [i for i, r in enumerate(test) if source == "all" or r["source"] == source]
                m = evaluate_spans([bio_to_spans(test[i][key]) for i in idx], [pred[i] for i in idx])
                rows.append({"system": f"dictionary_{version}", "layer": layer, "source": source, "case": case,
                             "min_precision": th, "dict_size": len(d), **m})
    pd.DataFrame(rows).round(4).to_csv(ROOT / "results" / "dictionary_test.csv", index=False)
    meta = {"command": "python src/02_dictionary_baseline.py --test", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seconds": round(time.time() - t0, 1), "settings_from": "results/dictionary_dev.csv (dev exact F1)"}
    (ROOT / "runs" / "dictionary_test_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(pd.DataFrame(rows).query("source == 'all'")[["system", "layer", "case", "min_precision", "dict_size", "exact_p",
                                                      "exact_r", "exact_f1", "partial_f1"]].round(4).to_string(index=False))


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_main()
    else:
        main()
