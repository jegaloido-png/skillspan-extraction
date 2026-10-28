"""Figures for the report, built only from the CSV files in results/ (no hard-coded numbers)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
R = ROOT / "results"

plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 9.5, "axes.titleweight": "bold", "figure.dpi": 150})
# Okabe-Ito colour-blind safe palette
C = {"dictionary_pure": "#BBBBBB", "dictionary_tuned": "#7F7F7F", "bert": "#0072B2", "jobbert": "#D55E00"}
NAMES = {"dictionary_pure": "Dictionary\n(no threshold)", "dictionary_tuned": "Dictionary\n(tuned on dev)",
         "bert": "BERT-base", "jobbert": "JobBERT"}
ORDER = ["dictionary_pure", "dictionary_tuned", "bert", "jobbert"]
LAYERS = [("skill", "Skill"), ("knowledge", "Knowledge")]

summ = pd.read_csv(R / "test_results_summary.csv")
runs = pd.read_csv(R / "test_results_per_run.csv")
tax = pd.read_csv(R / "error_taxonomy.csv")
rec = pd.read_csv(R / "recall_seen_unseen.csv")
lr = pd.read_csv(R / "lr_search_dev.csv")


def fig_main():
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), sharey=True)
    w = 0.38
    for ax, (layer, title) in zip(axes, LAYERS):
        for i, s in enumerate(ORDER):
            r = summ[(summ.system == s) & (summ.layer == layer) & (summ.source == "all")].iloc[0]
            for j, (m, hatch, alpha) in enumerate((("exact_f1", None, 1.0), ("partial_f1", "////", 0.55))):
                x = i + (j - 0.5) * w
                err = r[m + "_std"] if r.n_seeds > 1 else 0
                ax.bar(x, r[m + "_mean"], w, color=C[s], alpha=alpha, hatch=hatch, edgecolor="white", linewidth=0.5,
                       yerr=err if err else None, capsize=2, error_kw={"elinewidth": 0.8})
                ax.text(x, r[m + "_mean"] + (err or 0) + 0.012, f"{r[m + '_mean']:.2f}", ha="center", va="bottom",
                        fontsize=7)
            if s in ("bert", "jobbert"):
                pts = runs[(runs.system == s) & (runs.layer == layer) & (runs.source == "all")].exact_f1
                ax.scatter(np.full(len(pts), i - 0.5 * w) + np.linspace(-0.07, 0.07, len(pts)), pts, s=6,
                           color="black", zorder=3, linewidths=0)
        ax.set_xticks(range(len(ORDER)))
        ax.set_xticklabels([NAMES[s] for s in ORDER], fontsize=6.6)
        ax.set_title(title)
        ax.set_ylim(0, 0.95)
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("F1 on test (micro, span level)")
    axes[1].legend(handles=[Patch(facecolor="#555", label="exact match"),
                            Patch(facecolor="#555", alpha=0.55, hatch="////", edgecolor="white", label="partial match")],
                   loc="upper left", frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig_main_results.png", dpi=300)
    plt.close(fig)


def fig_errors():
    sysorder = ["dictionary", "bert", "jobbert"]
    lab = {"dictionary": "Dictionary", "bert": "BERT-base", "jobbert": "JobBERT"}
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 3.9))
    gold_cols = [("found", "#009E73", "exact"), ("gold_boundary_only", "#E69F00", "found, wrong boundaries"),
                 ("missed", "#CC3311", "missed")]
    pred_cols = [("pred_exact", "#009E73", "exact"), ("shorter", "#56B4E9", "too short"),
                 ("longer", "#0072B2", "too long"), ("shifted", "#CC79A7", "shifted"),
                 ("spurious", "#CC3311", "no overlap")]
    for k, (layer, title) in enumerate(LAYERS):
        t = tax[(tax.layer == layer) & (tax.source == "all")].set_index("system").loc[sysorder].copy()
        t["found"] = t.n_gold - t.missed - t.gold_boundary_only
        for row, cols, denom, head in ((0, gold_cols, "n_gold", "gold spans"), (1, pred_cols, "n_pred", "predicted spans")):
            ax = axes[row, k]
            left = np.zeros(len(t))
            for col, colour, label in cols:
                v = t[col].to_numpy() / t[denom].to_numpy()
                ax.barh(range(len(t)), v, left=left, color=colour, edgecolor="white", linewidth=0.5, label=label)
                for y, (a, b) in enumerate(zip(left, v)):
                    if b > 0.06:
                        ax.text(a + b / 2, y, f"{b * 100:.0f}", ha="center", va="center", fontsize=7, color="white")
                left += v
            ax.set_yticks(range(len(t)))
            ax.set_yticklabels([lab[s] for s in sysorder])
            ax.invert_yaxis()
            ax.set_xlim(0, 1)
            ax.set_xticks([0, .25, .5, .75, 1])
            ax.set_xticklabels(["0", "25", "50", "75", "100"])
            ax.set_title(f"{title}: share of {head} (%)", fontsize=8.5)
    for row in (0, 1):
        h, l = axes[row, 0].get_legend_handles_labels()
        axes[row, 0].legend(h, l, loc="upper left", bbox_to_anchor=(0.0, -0.17), ncol=len(h), frameon=False,
                            fontsize=7, handlelength=1.2, columnspacing=1.0)
    fig.tight_layout(h_pad=2.2)
    fig.savefig(OUT / "fig_error_breakdown.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_seen_unseen():
    sysorder = ["dictionary", "bert", "jobbert"]
    colour = {"dictionary": C["dictionary_tuned"], "bert": C["bert"], "jobbert": C["jobbert"]}
    lab = {"dictionary": "Dictionary", "bert": "BERT-base", "jobbert": "JobBERT"}
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.3), sharey=True)
    for ax, (layer, title) in zip(axes, LAYERS):
        d = rec[rec.layer == layer].set_index("system")
        n_seen, n_unseen = d.seen_gold.iloc[0], d.unseen_gold.iloc[0]
        for i, s in enumerate(sysorder):
            for j, col in enumerate(("seen_exact_recall", "unseen_exact_recall")):
                x = j + (i - 1) * 0.26
                ax.bar(x, d.loc[s, col], 0.24, color=colour[s], label=lab[s] if j == 0 else None)
                ax.text(x, d.loc[s, col] + 0.015, f"{d.loc[s, col]:.2f}", ha="center", fontsize=7)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([f"seen in training\n(n = {n_seen:.0f})", f"not seen in training\n(n = {n_unseen:.0f})"])
        ax.set_ylim(0, 1.05)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("exact recall on test")
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_seen_unseen.png", dpi=300)
    plt.close(fig)


def fig_lr():
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.1))
    colour = {"bert": C["bert"], "jobbert": C["jobbert"]}
    lab = {"bert": "BERT-base", "jobbert": "JobBERT"}
    for ax, (layer, title) in zip(axes, LAYERS):
        for m in ("bert", "jobbert"):
            d = lr[(lr.layer == layer) & (lr.model == m)].sort_values("lr")
            ax.plot(d.lr, d.dev_exact_f1, marker="o", ms=4, color=colour[m], label=lab[m])
        ax.set_xscale("log")
        ax.set_xticks([2e-5, 3e-5, 5e-5, 7e-5])
        ax.set_xticklabels(["2e-5", "3e-5", "5e-5", "7e-5"])
        ax.minorticks_off()
        ax.axvline(5e-5, color="black", lw=0.7, ls=":")
        ax.set_title(title)
        ax.set_xlabel("learning rate")
        ax.grid(alpha=0.25, linewidth=0.5)
    axes[0].set_ylabel("dev exact F1 (1 seed)")
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_lr_dev.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    fig_main()
    fig_errors()
    fig_seen_unseen()
    fig_lr()
    print("figures written to", OUT)
