"""
Quantum DevOps Mining — Analisi tassonomia finale
Genera 4 grafici sulla tassonomia emergente dai 4 batch di coding.

Uso:
    python taxonomy_analysis.py
"""

import json
import os
import textwrap
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Palette 

C_BLUE   = "#2E6DA4"
C_TEAL   = "#2E8B6A"
C_AMBER  = "#B07D2E"
C_ROSE   = "#9E3B4A"
C_GRID   = "#D8D8D8"
C_TEXT   = "#1A1A1A"
C_MUTED  = "#666666"

BATCH_COLORS = [C_BLUE, C_TEAL, C_AMBER, C_ROSE]
BATCH_LABELS = ["Batch 1", "Batch 2", "Batch 3", "Batch 4"]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "x",
    "grid.color": C_GRID,
    "grid.linewidth": 0.6,
    "figure.dpi": 150,
    "text.color": C_TEXT,
    "axes.labelcolor": C_TEXT,
    "xtick.color": C_TEXT,
    "ytick.color": C_TEXT,
})

PHASES_ALL = ["PLAN", "CODE", "BUILD", "TEST", "EVALUATE", "DEPLOY_CONFIGURE", "MONITOR", "RELEASE"]

# Estensioni fasi aggiunte nel batch 4 (non presenti nei file strutturati)
PHASE_EXTENSIONS_B4 = {
    "CAT4":  ["DEPLOY_CONFIGURE"],
    "CAT8":  ["TEST"],
    "CAT11": ["TEST"],
    "CAT12": ["TEST"],
}


# Lettura dati dai file JSON

def load_json(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_taxonomy_data():
    """
    Legge i 4 file campione_0X_inclusi_merge.json e costruisce:
    - CUMULATIVE: {cat_id: [n_b1, n_b2, n_b3, n_b4]}
    - CAT_PHASES: {cat_id: [fasi]} (da batch 3, esteso con B4)
    - CAT_LABELS: {cat_id: label breve per i grafici} (da macro_categoria)
    """
    # Batch 1-3: struttura con "categorie"
    cumulative = defaultdict(lambda: [0, 0, 0, 0])
    cat_phases = {}
    cat_macro  = {}

    for batch_idx, filename in enumerate([
        "campione_01_inclusi_merge.json",
        "campione_02_inclusi_merge.json",
        "campione_03_inclusi_merge.json",
    ]):
        data = load_json(filename)
        for cat in data["categorie"]:
            cid = cat["id_categoria"]
            cumulative[cid][batch_idx] = cat["n_porzioni_aggregate"]
            if batch_idx == 2:  # prendi fasi e nome dal batch 3 (più aggiornato)
                cat_phases[cid] = list(cat["fasi_devops_associate"])
                cat_macro[cid]  = cat["macro_categoria"]

    # Batch 4: struttura con "mappature" — conta le porzioni per categoria
    data4 = load_json("campione_04_inclusi_merge.json")
    b4_counts = defaultdict(int)
    for m in data4["mappature"]:
        b4_counts[m["categoria"]] += 1

    for cid, delta in b4_counts.items():
        cumulative[cid][3] = cumulative[cid][2] + delta

    # Per le categorie non toccate dal batch 4, B4 = B3
    for cid in cumulative:
        if cumulative[cid][3] == 0 and cumulative[cid][2] > 0:
            cumulative[cid][3] = cumulative[cid][2]

    # Applica estensioni fasi batch 4
    for cid, extra_phases in PHASE_EXTENSIONS_B4.items():
        if cid in cat_phases:
            for p in extra_phases:
                if p not in cat_phases[cid]:
                    cat_phases[cid].append(p)

    # Label brevi: prima riga della macro_categoria (fino a ~35 char, su 2 righe)
    cat_labels = {}
    for cid, macro in cat_macro.items():
        wrapped = textwrap.wrap(macro, width=32)
        cat_labels[cid] = "\n".join(wrapped[:2])

    cats = sorted(cumulative.keys(), key=lambda c: int(c.replace("CAT", "")))
    return cats, dict(cumulative), cat_phases, cat_labels


# Grafico 1: Porzioni finali per categoria 

def plot_final_counts(cats, cumulative, cat_labels):
    final = {c: cumulative[c][3] for c in cats}
    cats_sorted = sorted(cats, key=lambda c: final[c], reverse=True)
    labels = [cat_labels.get(c, c) for c in cats_sorted]
    values = [final[c] for c in cats_sorted]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(labels, values, color=C_BLUE, height=0.6, linewidth=0, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(val + 0.2, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", ha="left", fontsize=9, color=C_TEXT)

    ax.set_xlabel("Numero di porzioni codificate", color=C_MUTED, fontsize=9)
    ax.set_title("Distribuzione porzioni per categoria (tassonomia finale — 4 batch)",
                 fontsize=11, fontweight="bold", pad=12)
    ax.set_xlim(0, max(values) + 3)
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=8.5)
    ax.xaxis.grid(True, color=C_GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = os.path.join(SCRIPT_DIR, "plot_1_final_counts.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"Salvato: {out}")


# Grafico 2: Crescita per categoria per batch (stacked)

def plot_growth_stacked(cats, cumulative):
    final = {c: cumulative[c][3] for c in cats}
    cats_sorted = sorted(cats, key=lambda c: final[c], reverse=True)

    deltas = {}
    for cat in cats:
        cum = cumulative[cat]
        deltas[cat] = [
            cum[0],
            max(0, cum[1] - cum[0]),
            max(0, cum[2] - cum[1]),
            max(0, cum[3] - cum[2]),
        ]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(cats_sorted))
    bottoms = np.zeros(len(cats_sorted))

    for i, (color, label) in enumerate(zip(BATCH_COLORS, BATCH_LABELS)):
        vals = np.array([deltas[c][i] for c in cats_sorted])
        bars = ax.bar(x, vals, 0.6, bottom=bottoms,
                      color=color, label=label, linewidth=0, zorder=3)
        for bar, val, bot in zip(bars, vals, bottoms):
            if val >= 2:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bot + val / 2, str(int(val)),
                        ha="center", va="center", fontsize=7.5,
                        color="white", fontweight="bold")
        bottoms += vals

    ax.set_xticks(x)
    ax.set_xticklabels(cats_sorted, fontsize=9)
    ax.set_ylabel("Porzioni codificate", color=C_MUTED, fontsize=9)
    ax.set_title("Crescita delle porzioni per categoria e per batch",
                 fontsize=11, fontweight="bold", pad=12)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.8)
    ax.yaxis.grid(True, color=C_GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = os.path.join(SCRIPT_DIR, "plot_2_growth_stacked.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"Salvato: {out}")


# Grafico 3: Curva di saturazione

def plot_saturation(cats, cumulative):
    new_cats = [0, 0, 0, 0]
    for cat in cats:
        cum = cumulative[cat]
        for i in range(4):
            if cum[i] > 0 and (i == 0 or cum[i - 1] == 0):
                new_cats[i] += 1

    cumulative_cats = np.cumsum(new_cats)
    total_portions = [sum(cumulative[c][i] for c in cats) for i in range(4)]
    batches = [1, 2, 3, 4]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.bar(batches, total_portions, color=C_BLUE, alpha=0.25,
            width=0.5, zorder=2, label="Porzioni totali cumulative")
    for x, y in zip(batches, total_portions):
        ax1.text(x, y + 1, str(y), ha="center", va="bottom", fontsize=9, color=C_BLUE)

    ax1.set_xlabel("Batch", fontsize=10)
    ax1.set_ylabel("Porzioni codificate (cumulative)", color=C_BLUE, fontsize=9)
    ax1.tick_params(axis="y", labelcolor=C_BLUE)

    ax2 = ax1.twinx()
    ax2.plot(batches, cumulative_cats, color=C_ROSE, marker="o",
             markersize=8, linewidth=2, zorder=5, label="Categorie cumulative")
    ax2.plot(batches[-1], cumulative_cats[-1], "o", color=C_ROSE, markersize=12, zorder=6)
    for x, y in zip(batches, cumulative_cats):
        ax2.text(x + 0.07, y + 0.3, str(y), fontsize=9, color=C_ROSE, fontweight="bold")

    ax2.set_ylabel("Categorie emergenti (cumulative)", color=C_ROSE, fontsize=9)
    ax2.tick_params(axis="y", labelcolor=C_ROSE)
    ax2.set_ylim(0, 18)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(C_ROSE)
    ax2.annotate("SATURA\n(0 nuove categorie)", xy=(4, 14),
                 xytext=(3.3, 16.5),
                 arrowprops=dict(arrowstyle="->", color=C_ROSE, lw=1.2),
                 fontsize=8.5, color=C_ROSE, ha="center")

    ax1.set_title("Curva di saturazione teorica", fontsize=11, fontweight="bold", pad=12)
    ax1.set_xticks(batches)
    ax1.set_xticklabels([f"Batch {i}" for i in batches])
    ax1.yaxis.grid(True, color=C_GRID, linewidth=0.6, zorder=0)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper left", framealpha=0.8)

    plt.tight_layout()
    out = os.path.join(SCRIPT_DIR, "plot_3_saturation.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"Salvato: {out}")


# Grafico 4: Heatmap categoria × fase DevOps

def plot_phase_heatmap(cats, cumulative, cat_phases):
    final = {c: cumulative[c][3] for c in cats}
    matrix = np.zeros((len(cats), len(PHASES_ALL)))
    for i, cat in enumerate(cats):
        for j, phase in enumerate(PHASES_ALL):
            if phase in cat_phases.get(cat, []):
                matrix[i][j] = final[cat]

    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=max(final.values()))

    ax.set_xticks(range(len(PHASES_ALL)))
    ax.set_xticklabels(PHASES_ALL, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels(cats, fontsize=9)

    for i in range(len(cats)):
        for j in range(len(PHASES_ALL)):
            val = int(matrix[i][j])
            if val > 0:
                text_color = "white" if val > 10 else C_TEXT
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=8.5, color=text_color, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Porzioni codificate", fontsize=9, color=C_MUTED)
    ax.set_title("Copertura categoria × fase DevOps (tassonomia finale)",
                 fontsize=11, fontweight="bold", pad=12)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)

    plt.tight_layout()
    out = os.path.join(SCRIPT_DIR, "plot_4_phase_heatmap.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"Salvato: {out}")


# Main

if __name__ == "__main__":
    cats, cumulative, cat_phases, cat_labels = build_taxonomy_data()

    final_counts = {c: cumulative[c][3] for c in cats}
    print("=== Quantum DevOps — Analisi tassonomia ===\n")
    print(f"Categorie totali: {len(cats)}")
    print(f"Porzioni totali: {sum(final_counts.values())}")
    print(f"Fasi DevOps coperte: {len(PHASES_ALL)}\n")

    print("Generazione grafici...")
    plot_final_counts(cats, cumulative, cat_labels)
    plot_growth_stacked(cats, cumulative)
    plot_saturation(cats, cumulative)
    plot_phase_heatmap(cats, cumulative, cat_phases)

    print("\nFatto. 4 file PNG salvati nella cartella del progetto.")
