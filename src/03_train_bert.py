"""Fine-tune a BERT-style encoder for BIO token classification on SkillSpan.

One run = one (model, layer, learning rate, seed). Layers are trained separately
(--layer skill | knowledge), as decided for the project.

Example:
  python src/03_train_bert.py --model bert --layer skill --lr 3e-5 --seed 3477689
  python src/03_train_bert.py --model distilbert --layer skill --max_train 500 --max_dev 300 --epochs 1   # smoke test

Protocol:
  - weights are learned on TRAIN only;
  - DEV is used after every epoch to pick the best epoch (and, across runs, the learning rate);
  - TEST is touched only with --predict_test (final runs), using the best-dev epoch.
Resume: a run whose metrics.json already exists is skipped (use --force to redo it).
"""
import argparse
import importlib.util
import json
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import transformers
from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SRC / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


data_mod = _load("load_data", "01_load_data.py")
eval_mod = _load("evaluate", "04_evaluate.py")
load_split, bio_to_spans, TAG_KEYS = data_mod.load_split, data_mod.bio_to_spans, data_mod.TAG_KEYS
evaluate_spans = eval_mod.evaluate_spans

MODELS = {
    "bert": "google-bert/bert-base-cased",
    "jobbert": "jjzha/jobbert-base-cased",
    "distilbert": "distilbert/distilbert-base-cased",  # debug only
}
LABELS = ["O", "B", "I"]
L2I = {l: i for i, l in enumerate(LABELS)}


def encode(rows, tok, key, max_len):
    """Tokenize pre-split words; the label of a word goes on its FIRST sub-token, the rest get -100."""
    enc = tok([r["tokens"] for r in rows], is_split_into_words=True, truncation=True, max_length=max_len)
    feats, truncated = [], 0
    for i, r in enumerate(rows):
        word_ids, labels, prev = enc.word_ids(i), [], None
        for w in word_ids:
            labels.append(-100 if (w is None or w == prev) else L2I[r[key][w]])
            prev = w
        if max((w for w in word_ids if w is not None), default=-1) + 1 < len(r["tokens"]):
            truncated += 1
        feats.append({"input_ids": enc["input_ids"][i], "attention_mask": enc["attention_mask"][i],
                      "labels": labels, "word_ids": word_ids, "n_words": len(r["tokens"])})
    return feats, truncated


def batches(feats, bs, pad_id, rng=None):
    idx = list(range(len(feats)))
    if rng is not None:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        chunk = [feats[j] for j in idx[i:i + bs]]
        L = max(len(f["input_ids"]) for f in chunk)

        def pad(name, v):
            return torch.tensor([f[name] + [v] * (L - len(f[name])) for f in chunk])

        yield chunk, {"input_ids": pad("input_ids", pad_id), "attention_mask": pad("attention_mask", 0),
                      "labels": pad("labels", -100)}


@torch.no_grad()
def predict_tags(model, feats, bs, pad_id, device):
    """Return one BIO tag list per sentence (word level, from the first sub-token)."""
    model.eval()
    out = []
    for chunk, b in batches(feats, bs, pad_id):
        logits = model(input_ids=b["input_ids"].to(device), attention_mask=b["attention_mask"].to(device)).logits
        for f, row in zip(chunk, logits.argmax(-1).cpu().tolist()):
            tags, prev = ["O"] * f["n_words"], None
            for pos, w in enumerate(f["word_ids"]):
                if w is not None and w != prev:
                    tags[w] = LABELS[row[pos]]
                prev = w
            out.append(tags)
    return out


def score(rows, pred_tags, key):
    """Exact + partial span P/R/F1 overall and per source."""
    res = {}
    for source in ("all", "house", "tech"):
        sel = [i for i, r in enumerate(rows) if source == "all" or r["source"] == source]
        gold = [bio_to_spans(rows[i][key]) for i in sel]
        pred = [bio_to_spans(pred_tags[i]) for i in sel]
        res[source] = evaluate_spans(gold, pred)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--layer", choices=TAG_KEYS, required=True)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--seed", type=int, default=3477689)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--patience", type=int, default=3, help="stop if dev F1 does not improve for this many epochs")
    ap.add_argument("--batch_size", type=int, default=16)
    ap.add_argument("--max_len", type=int, default=256)
    ap.add_argument("--warmup", type=float, default=0.1)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--max_train", type=int, default=None, help="subset for smoke tests")
    ap.add_argument("--max_dev", type=int, default=None)
    ap.add_argument("--predict_test", action="store_true", help="final runs only: predict test with best-dev epoch")
    ap.add_argument("--no_amp", action="store_true")
    ap.add_argument("--out_dir", default=str(ROOT / "runs"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    subset = args.max_train is not None or args.max_dev is not None
    name = f"{args.model}_{args.layer}_lr{args.lr:g}_seed{args.seed}" + ("_subset" if subset else "")
    run_dir = Path(args.out_dir) / name
    if (run_dir / "metrics.json").exists() and not args.force:
        print(f"[skip] {name}: metrics.json exists")
        return
    run_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    rng = random.Random(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    key = TAG_KEYS[args.layer]
    t0 = time.time()

    train, dev = load_split("train"), load_split("dev")
    if args.max_train:
        train = train[:args.max_train]
    if args.max_dev:
        dev = dev[:args.max_dev]

    tok = AutoTokenizer.from_pretrained(MODELS[args.model])
    model = AutoModelForTokenClassification.from_pretrained(
        MODELS[args.model], num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=L2I).to(device)
    train_f, trunc_train = encode(train, tok, key, args.max_len)
    dev_f, trunc_dev = encode(dev, tok, key, args.max_len)
    pad_id = tok.pad_token_id

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    steps = args.epochs * ((len(train_f) + args.batch_size - 1) // args.batch_size)
    sched = get_linear_schedule_with_warmup(opt, int(args.warmup * steps), steps)
    use_amp = device == "cuda" and not args.no_amp
    amp_dtype = torch.bfloat16 if (use_amp and torch.cuda.is_bf16_supported()) else torch.float16
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and amp_dtype == torch.float16)

    history, best_f1, best_epoch, best_state, best_dev_pred, bad = [], -1.0, 0, None, None, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        total, n = 0.0, 0
        for _, b in batches(train_f, args.batch_size, pad_id, rng):
            b = {k: v.to(device) for k, v in b.items()}
            with torch.autocast(device_type=device, dtype=amp_dtype, enabled=use_amp):
                loss = model(**b).loss
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
            n += 1
        dev_pred = predict_tags(model, dev_f, args.batch_size, pad_id, device)
        dev_scores = score(dev, dev_pred, key)
        history.append({"epoch": epoch, "train_loss": round(total / max(1, n), 4),
                        "dev_exact_f1": round(dev_scores["all"]["exact_f1"], 4),
                        "dev_partial_f1": round(dev_scores["all"]["partial_f1"], 4),
                        "seconds": round(time.time() - t0, 1)})
        print(history[-1], flush=True)
        if dev_scores["all"]["exact_f1"] > best_f1:
            best_f1, best_epoch, bad = dev_scores["all"]["exact_f1"], epoch, 0
            best_dev_pred, best_dev_scores = dev_pred, dev_scores
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= args.patience:
                break

    (run_dir / "dev_pred.json").write_text(json.dumps(best_dev_pred), encoding="utf-8")
    result = {"best_epoch": best_epoch, "dev": best_dev_scores}
    if args.predict_test:
        model.load_state_dict(best_state)
        test = load_split("test")
        test_f, trunc_test = encode(test, tok, key, args.max_len)
        test_pred = predict_tags(model, test_f, args.batch_size, pad_id, device)
        (run_dir / "test_pred.json").write_text(json.dumps(test_pred), encoding="utf-8")
        result["test"] = score(test, test_pred, key)
        result["truncated_sentences_test"] = trunc_test

    meta = {
        "command": "python " + " ".join(sys.argv), "config": vars(args), "hf_model": MODELS[args.model],
        "model_commit": getattr(model.config, "_commit_hash", None),
        "versions": {"python": platform.python_version(), "torch": torch.__version__,
                     "transformers": transformers.__version__, "numpy": np.__version__},
        "device": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
        "amp": str(amp_dtype) if use_amp else "off",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t0, 1),
        "truncated_sentences": {"train": trunc_train, "dev": trunc_dev},
        "n_train": len(train_f), "n_dev": len(dev_f), "history": history, **result,
    }
    (run_dir / "metrics.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")  # written last = run complete
    print(f"[done] {name}: best epoch {best_epoch}, dev exact F1 {best_f1:.4f}, {meta['seconds']}s")


if __name__ == "__main__":
    main()
