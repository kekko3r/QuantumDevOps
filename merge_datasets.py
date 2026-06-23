"""
Quantum DevOps Mining — Dataset Merger
Aggrega i dataset di tutte le fonti in un corpus unico.

Operazioni:
1. Carica tutti i dataset JSON specificati
2. Deduplica per URL (criterio automatico)
3. Applica criteri tecnici automatizzabili:
   - Rimuove thread con body assente o troppo corto (< 30 caratteri)
   - Rimuove thread con titolo assente
4. Salva il corpus completo filtrato

I criteri qualitativi (teorico puro, bug report, rilevanza DevOps,
lingua inglese) richiedono lettura umana e vengono applicati
durante lo screening manuale sul campione estratto da sampler.py.

Uso:
    python merge_datasets.py --inputs dataset_github.json dataset_so.json dataset_qcse.json --output corpus_completo.json
"""

import json
import argparse
import os
from datetime import datetime, timezone


# ─── Caricamento ───

def load_dataset(filepath):
    """Carica un dataset JSON. Supporta sia formato {threads: [...]} che lista diretta."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        threads = data
    elif isinstance(data, dict):
        threads = data.get("threads", [])
    else:
        print(f"  Formato non riconosciuto: {filepath}")
        return []

    print(f"  {filepath}: {len(threads)} thread caricati")
    return threads


# ─── Deduplica ───

def deduplicate(threads):
    """Rimuove duplicati basandosi sull'URL."""
    seen = set()
    unique = []
    for t in threads:
        url = t.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(t)
    return unique


# ─── Criteri tecnici automatizzabili ───

def apply_technical_filters(threads):
    """
    Applica i criteri di esclusione automatizzabili.
    I criteri qualitativi vengono applicati manualmente durante lo screening.

    Criteri applicati:
    - Titolo assente o vuoto
    - Body assente o troppo corto (< 30 caratteri) — placeholder o spam tecnico

    Aggiunge inoltre "flag_zero_risposte": non esclude nulla, segnala solo i
    thread senza commenti/risposte per dare priorità nello screening manuale
    (il criterio di esclusione vero richiede giudizio su ambiguità, non solo
    il conteggio).
    """
    filtered = []
    excluded = {"no_titolo": 0, "body_vuoto": 0, "body_troppo_corto": 0}

    for t in threads:
        titolo = (t.get("titolo") or "").strip()
        body = (t.get("body") or "").strip()

        if not titolo:
            excluded["no_titolo"] += 1
            continue

        if not body:
            excluded["body_vuoto"] += 1
            continue

        if len(body) < 30:
            excluded["body_troppo_corto"] += 1
            continue

        t["flag_zero_risposte"] = t.get("numero_commenti", 0) == 0
        filtered.append(t)

    print(f"  Esclusi per titolo mancante: {excluded['no_titolo']}")
    print(f"  Esclusi per body vuoto: {excluded['body_vuoto']}")
    print(f"  Esclusi per body troppo corto: {excluded['body_troppo_corto']}")
    print(f"  Totale esclusi (criteri tecnici): {sum(excluded.values())}")

    zero_risposte = sum(1 for t in filtered if t["flag_zero_risposte"])
    print(f"  Flaggati zero risposte (non esclusi, da rivedere manualmente): {zero_risposte}")

    return filtered


# ─── Statistiche ───

def compute_stats(threads):
    """Calcola statistiche di distribuzione per fonte e fase."""
    stats_fonte = {}
    stats_fase = {}
    stats_tipo = {}

    for t in threads:
        fonte = t.get("fonte", "unknown")
        fase = t.get("fase_query", "unknown")
        tipo = t.get("tipo", "unknown")

        stats_fonte[fonte] = stats_fonte.get(fonte, 0) + 1
        stats_fase[fase] = stats_fase.get(fase, 0) + 1
        stats_tipo[tipo] = stats_tipo.get(tipo, 0) + 1

    return stats_fonte, stats_fase, stats_tipo


# ─── Main ───

def main(input_files, output_file):

    print("=== QUANTUM DEVOPS MINING — Merge Dataset ===\n")

    # 1. Carica tutti i dataset
    all_threads = []
    for filepath in input_files:
        if not os.path.exists(filepath):
            print(f"  ATTENZIONE: file non trovato — {filepath}")
            continue
        threads = load_dataset(filepath)
        all_threads.extend(threads)

    print(f"\nTotale thread caricati: {len(all_threads)}")

    # 2. Deduplica
    all_threads = deduplicate(all_threads)
    print(f"Totale dopo deduplica: {len(all_threads)}")

    # 3. Criteri tecnici automatizzabili
    print("\nApplico criteri tecnici automatizzabili...")
    all_threads = apply_technical_filters(all_threads)
    print(f"Totale dopo filtri tecnici: {len(all_threads)}")

    # 4. Statistiche
    stats_fonte, stats_fase, stats_tipo = compute_stats(all_threads)

    print("\nDistribuzione per fonte:")
    for k, v in sorted(stats_fonte.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nDistribuzione per fase:")
    for k, v in sorted(stats_fase.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nDistribuzione per tipo:")
    for k, v in sorted(stats_tipo.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    # 5. Salva corpus completo
    output = {
        "metadata": {
            "data_creazione": datetime.now(tz=timezone.utc).isoformat(),
            "fonti_input": input_files,
            "totale_thread": len(all_threads),
            "distribuzione_fonte": stats_fonte,
            "distribuzione_fase": stats_fase,
            "distribuzione_tipo": stats_tipo,
            "note": (
                "Corpus grezzo filtrato per criteri tecnici automatizzabili. "
                "I criteri qualitativi (teorico puro, bug report, rilevanza "
                "DevOps, lingua) vengono applicati manualmente durante lo "
                "screening del campione estratto da sampler.py."
            )
        },
        "threads": all_threads
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nCorpus completo salvato in: {output_file}")
    print(f"Thread pronti per il campionamento: {len(all_threads)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum DevOps Dataset Merger")
    parser.add_argument(
        "--inputs", nargs="+", required=True,
        help="File dataset da unire (es. dataset_github.json dataset_so.json dataset_qcse.json)"
    )
    parser.add_argument(
        "--output", default="corpus_completo.json",
        help="File di output (default: corpus_completo.json)"
    )
    args = parser.parse_args()

    main(args.inputs, args.output)
