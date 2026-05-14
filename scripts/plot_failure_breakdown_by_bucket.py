#!/usr/bin/env python3
"""Plot failure-category breakdown stacked by potency-ratio bucket, per agent."""
from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "docs/findings/pairwise-sequence-calibration/failure_classifications.csv"
OUT_PATH = ROOT / "docs/findings/pairwise-sequence-calibration/failure_breakdown_by_bucket.png"

# bucket -> human label (widest ratio first)
BUCKET_ORDER = ["trivial", "easy", "medium", "hard"]
BUCKET_LABEL = {
    "trivial": ">10×",
    "easy": "3–10×",
    "medium": "1.5–3×",
    "hard": "1.1–1.5×",
}

CATEGORY_ORDER = [
    "length_or_complexity_cue",
    "pharmacophore_misapplied",
    "aup_refusal",
    "no_substantive_reasoning",
]
CATEGORY_LABEL = {
    "length_or_complexity_cue": "Length / complexity cue",
    "pharmacophore_misapplied": "Pharmacophore misapplied",
    "aup_refusal": "AUP refusal",
    "no_substantive_reasoning": "No substantive reasoning",
}
CATEGORY_COLOR = {
    "length_or_complexity_cue": "#d95f02",
    "pharmacophore_misapplied": "#1b9e77",
    "aup_refusal": "#e7298a",
    "no_substantive_reasoning": "#666666",
}

AGENTS = ["claude", "codex"]
N_PER_BUCKET = 15  # 3 families × 5 pairs

def load_counts():
    counts = {a: {b: {c: 0 for c in CATEGORY_ORDER} for b in BUCKET_ORDER} for a in AGENTS}
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            agent = row["agent"]
            bucket = row["bucket"]
            cat = row["category"]
            if agent in counts and bucket in counts[agent] and cat in CATEGORY_ORDER:
                counts[agent][bucket][cat] += 1
    return counts

def main():
    counts = load_counts()

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    x = np.arange(len(BUCKET_ORDER))
    width = 0.6

    for ax, agent in zip(axes, AGENTS):
        bottom = np.zeros(len(BUCKET_ORDER))
        for cat in CATEGORY_ORDER:
            heights = np.array([counts[agent][b][cat] for b in BUCKET_ORDER])
            ax.bar(
                x,
                heights,
                width,
                bottom=bottom,
                label=CATEGORY_LABEL[cat],
                color=CATEGORY_COLOR[cat],
                edgecolor="white",
                linewidth=0.5,
            )
            for xi, (h, b0) in enumerate(zip(heights, bottom)):
                if h > 0:
                    ax.text(
                        xi,
                        b0 + h / 2,
                        str(int(h)),
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="white",
                        fontweight="bold",
                    )
            bottom += heights

        totals = bottom.astype(int)
        for xi, total in enumerate(totals):
            ax.text(
                xi,
                total + 0.3,
                f"{total}/{N_PER_BUCKET}",
                ha="center",
                va="bottom",
                fontsize=9,
                color="black",
            )

        ax.set_xticks(x)
        ax.set_xticklabels([BUCKET_LABEL[b] for b in BUCKET_ORDER])
        ax.set_title(f"{agent}", fontsize=13)
        ax.set_xlabel("Potency ratio (widest → narrowest)")
        ax.set_ylim(0, N_PER_BUCKET + 1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle=":", alpha=0.4)

    axes[0].set_ylabel(f"Failure count (out of {N_PER_BUCKET} pairs per bin)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=len(CATEGORY_ORDER),
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.suptitle(
        "Breakdown of failures in pairwise potency predictions",
        fontsize=14,
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
    print(f"wrote {OUT_PATH}")

    print("\nTotals by agent × bucket:")
    for a in AGENTS:
        for b in BUCKET_ORDER:
            row = counts[a][b]
            total = sum(row.values())
            parts = ", ".join(f"{CATEGORY_LABEL[c]}={row[c]}" for c in CATEGORY_ORDER if row[c])
            print(f"  {a} {b} ({BUCKET_LABEL[b]}): {total} failures — {parts}")

if __name__ == "__main__":
    main()
