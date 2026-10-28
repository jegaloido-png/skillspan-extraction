"""Span-level metrics shared by all systems (dictionary and BERT).

Only the metric functions live here for now; the CLI that evaluates saved
predictions on the test set is added in step 5.

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
