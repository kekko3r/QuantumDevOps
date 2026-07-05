"""
Quantum DevOps Mining — Sampler
Estrae campioni casuali dal corpus completo per il coding iterativo.

Come da indicazione del prof (Palomba):
- Primo batch: 100 thread casuali
- Batch successivi: N thread casuali dagli ancora non campionati
- Si continua fino alla saturazione teorica

Lo script trova automaticamente i batch precedenti (campione_*.json)
nella stessa cartella dell'output e li esclude dal nuovo campione.
Il seed viene incrementato automaticamente in base al numero di batch.

Uso:
    # Primo batch (100 thread) — trova automaticamente batch precedenti
    python sampler.py --corpus corpus_completo.json --output campione_01.json

    # Batch successivi — stesso comando, cambia solo il nome output
    python sampler.py --corpus corpus_completo.json --output campione_02.json
    python sampler.py --corpus corpus_completo.json --output campione_03.json

    # Dimensione personalizzata
    python sampler.py --corpus corpus_completo.json --output campione_02.json --size 150
"""

import json
import argparse
import os
import re
import random
import glob
from datetime import datetime, timezone


# ─── Caricamento ─────────────────────────────────────────────────────────────

def load_corpus(filepath):
    """Carica il corpus completo."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    threads = data.get("threads", []) if isinstance(data, dict) else data
    print(f"Corpus caricato: {len(threads)} thread")
    return threads


def find_previous_batches(output_file):
    """
    Trova automaticamente i file campione_*.json nella stessa cartella
    dell'output, escludendo il file di output corrente.
    """
    output_dir = os.path.dirname(os.path.abspath(output_file))
    pattern = os.path.join(output_dir, "campione_*.json")
    found = sorted(glob.glob(pattern))
    # Mantieni solo batch reali: campione_NN.json (solo cifre dopo underscore)
    found = [f for f in found if re.match(r"campione_\d+\.json$", os.path.basename(f))]
    # Esclude il file di output corrente se già esiste
    found = [f for f in found if os.path.abspath(f) != os.path.abspath(output_file)]
    return found


def load_already_sampled_urls(filepaths):
    """Carica gli URL dei thread già campionati nei batch precedenti."""
    already_sampled_urls = set()
    for filepath in filepaths:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        threads = data.get("threads", []) if isinstance(data, dict) else data
        urls = {t.get("url") for t in threads if t.get("url")}
        already_sampled_urls.update(urls)
        print(f"  {os.path.basename(filepath)}: {len(urls)} URL già campionati")
    return already_sampled_urls


# ─── Campionamento ────────────────────────────────────────────────────────────

def sample_threads(threads, already_sampled_urls, size, seed):
    """Estrae un campione casuale dai thread non ancora campionati."""
    available = [t for t in threads if t.get("url") not in already_sampled_urls]
    print(f"Thread disponibili (non ancora campionati): {len(available)}")

    if not available:
        print("ATTENZIONE: tutti i thread sono già stati campionati!")
        return []

    if len(available) < size:
        print(f"ATTENZIONE: disponibili solo {len(available)} thread, meno dei {size} richiesti.")
        size = len(available)

    random.seed(seed)
    return random.sample(available, size)


# ─── Statistiche ─────────────────────────────────────────────────────────────

def print_sample_stats(threads):
    """Stampa la distribuzione del campione per fonte e fase."""
    stats_fonte = {}
    stats_fase = {}

    for t in threads:
        fonte = t.get("fonte", "unknown")
        fase = t.get("fase_query", "unknown")
        stats_fonte[fonte] = stats_fonte.get(fonte, 0) + 1
        stats_fase[fase] = stats_fase.get(fase, 0) + 1

    print("\nDistribuzione campione per fonte:")
    for k, v in sorted(stats_fonte.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nDistribuzione campione per fase:")
    for k, v in sorted(stats_fase.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    flagged = sum(1 for t in threads if t.get("flag_zero_risposte"))
    print(f"\nThread con zero risposte: {flagged} (da valutare con attenzione)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(corpus_file, output_file, size):

    print("=== QUANTUM DEVOPS MINING — Sampler ===\n")

    # 1. Carica corpus
    threads = load_corpus(corpus_file)

    # 2. Trova automaticamente batch precedenti
    previous_batches = find_previous_batches(output_file)
    already_sampled_urls = set()

    if previous_batches:
        print(f"\nBatch precedenti trovati ({len(previous_batches)}):")
        already_sampled_urls = load_already_sampled_urls(previous_batches)
        print(f"Totale URL già campionati: {len(already_sampled_urls)}")
    else:
        print("Nessun batch precedente trovato — primo campionamento.")

    # 3. Seed automatico basato sul numero di batch esistenti
    seed = 42 + len(previous_batches)
    print(f"\nSeed automatico: {seed} (batch #{len(previous_batches) + 1})")

    # 4. Campiona
    print(f"Estraggo campione di {size} thread...")
    sampled = sample_threads(threads, already_sampled_urls, size, seed)

    if not sampled:
        print("Nessun thread da campionare. Uscita.")
        return

    print(f"Campione estratto: {len(sampled)} thread")
    print_sample_stats(sampled)

    # 5. Salva
    output = {
        "metadata": {
            "data_creazione": datetime.now(tz=timezone.utc).isoformat(),
            "corpus_sorgente": corpus_file,
            "batch_numero": len(previous_batches) + 1,
            "batch_precedenti": [os.path.basename(f) for f in previous_batches],
            "dimensione_campione": len(sampled),
            "seed": seed,
            "note": (
                "Campione casuale per screening manuale e coding iterativo. "
                "Applicare i criteri qualitativi di inclusione/esclusione "
                "prima di procedere con il coding."
            )
        },
        "threads": sampled
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nCampione salvato in: {output_file}")
    print(f"Batch #{len(previous_batches) + 1} — seed {seed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quantum DevOps Sampler — estrae campioni casuali per il coding iterativo"
    )
    parser.add_argument("--corpus", required=True, help="File corpus completo (output di merge_datasets.py)")
    parser.add_argument("--output", required=True, help="File di output del campione (es. campione_01.json)")
    parser.add_argument("--size", type=int, default=100, help="Dimensione del campione (default: 100)")
    args = parser.parse_args()

    main(args.corpus, args.output, args.size)
