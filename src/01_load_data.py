"""Load SkillSpan (JSON Lines) and print/save dataset statistics.

Usage: python src/01_load_data.py
Other scripts import load_split() and bio_to_spans() from here.
"""
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "json"
RESULTS_DIR = ROOT / "results"
SPLITS = ("train", "dev", "test")
# The two label layers: JSON key -> name used in the paper
TAG_KEYS = {"skill": "tags_skill", "knowledge": "tags_knowledge"}


def load_split(split):
    """Return the sentences of a split as a list of dicts (files are JSON Lines)."""
    path = DATA_DIR / f"{split}.json"
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    for r in rows:
        assert len(r["tokens"]) == len(r["tags_skill"]) == len(r["tags_knowledge"]), r
    return rows


def bio_to_spans(tags):
    """Convert a BIO tag list to (start, end_exclusive) spans.

    An I- tag that does not follow a B-/I- tag opens a new span (lenient reading);
    such cases are counted separately by check_bio().
    """
    spans, start = [], None
    for i, t in enumerate(tags):
        if t.startswith("B"):
            if start is not None:
                spans.append((start, i))
            start = i
        elif t.startswith("I"):
            if start is None:
                start = i
        else:
            if start is not None:
                spans.append((start, i))
                start = None
    if start is not None:
        spans.append((start, len(tags)))
    return spans


def check_bio(tags):
    """Count I- tags that do not continue a span (invalid BIO)."""
    bad, prev = 0, "O"
    for t in tags:
        if t.startswith("I") and prev == "O":
            bad += 1
        prev = t
    return bad


def compute_stats(data):
    """Build one row of stats per (split, source) and per (split, 'all')."""
    rows = []
    for split in SPLITS:
        for source in ("house", "tech", "all"):
            sents = [r for r in data[split] if source == "all" or r["source"] == source]
            row = {
                "split": split,
                "source": source,
                "sentences": len(sents),
                "tokens": sum(len(r["tokens"]) for r in sents),
            }
            row["avg_sent_len"] = round(row["tokens"] / max(1, row["sentences"]), 2)
            for name, key in TAG_KEYS.items():
                spans = [(e - s) for r in sents for s, e in bio_to_spans(r[key])]
                row[f"{name}_spans"] = len(spans)
                row[f"{name}_avg_span_len"] = round(sum(spans) / max(1, len(spans)), 2)
                row[f"{name}_sents_with_span"] = sum(1 for r in sents if any(t != "O" for t in r[key]))
            rows.append(row)
    return rows


def main():
    data = {s: load_split(s) for s in SPLITS}
    stats = compute_stats(data)

    tagset = Counter(t for s in SPLITS for r in data[s] for k in TAG_KEYS.values() for t in r[k])
    print("Tag set:", dict(tagset))
    for s in SPLITS:
        for name, key in TAG_KEYS.items():
            bad = sum(check_bio(r[key]) for r in data[s])
            if bad:
                print(f"WARNING {s}/{name}: {bad} I- tags not preceded by B-/I-")
    both = sum(1 for s in SPLITS for r in data[s]
               if any(t != "O" for t in r["tags_skill"]) and any(t != "O" for t in r["tags_knowledge"]))
    print("Sentences having both Skill and Knowledge spans:", both)

    try:
        import pandas as pd
    except ImportError:
        pd = None
    if pd is not None:
        df = pd.DataFrame(stats)
        RESULTS_DIR.mkdir(exist_ok=True)
        df.to_csv(RESULTS_DIR / "dataset_stats.csv", index=False)
        (RESULTS_DIR / "dataset_stats.md").write_text(df.to_markdown(index=False) if importlib.util.find_spec("tabulate") else df.to_string(index=False), encoding="utf-8")
        print(df.to_string(index=False))
    else:
        for r in stats:
            print(r)


if __name__ == "__main__":
    main()
