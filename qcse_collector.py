"""
Quantum DevOps Mining — Quantum Computing Stack Exchange Collector
Raccoglie domande e risposte da Quantum Computing Stack Exchange
rilevanti per il dominio Quantum DevOps.

Differenza rispetto a stackoverflow_collector.py:
- site = "quantumcomputing" invece di "stackoverflow"
- Nessun tag necessario: il CONTESTO quantum è implicito nel sito
  (a differenza di Stack Overflow, generalista, dove i tag servono
  a isolare le domande quantum dal resto del sito)
- Le keyword di fase vengono usate direttamente nel campo q

Stessa API Stack Exchange, stessa API Key, stessi limiti di quota:
- 300 richieste/giorno anonime
- 10.000 richieste/giorno con API Key
- Max 30 richieste/secondo (rispettato con time.sleep(1))

Uso:
    python qcse_collector.py --output dataset_qcse.json
    python qcse_collector.py --key YOUR_KEY --output dataset_qcse.json
"""

import requests
import json
import time
import argparse
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from queries import PHASE_QUERIES

load_dotenv()

# ─── Configurazione ───

BASE_URL = "https://api.stackexchange.com/2.3"

# Su Quantum Computing SE il CONTESTO è implicito nel sito —
# non servono tag: tutto il sito è quantum.
# Le keyword di fase filtrano la FASE direttamente.
SITE = "quantumcomputing"


# ─── Utility ───

def make_request(url, params):
    """Esegue una richiesta GET con gestione rate limit e quota."""
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()

        if "error_id" in data:
            print(f"  API errore {data['error_id']}: {data.get('error_message')}")
            return None

        # Backoff esplicito richiesto dall'API
        if data.get("backoff"):
            print(f"  Backoff richiesto: aspetto {data['backoff']} secondi...")
            time.sleep(data["backoff"])

        # Log quota residua per evitare esaurimento silenzioso
        quota = data.get("quota_remaining")
        if quota is not None and quota < 50:
            print(f"  ATTENZIONE: quota API residua = {quota}")

        return data
    else:
        print(f"  Errore {response.status_code}: {url}")
        return None


# ─── Raccolta Questions ───

def collect_questions_for_keyword(phase, keyword, api_key=None, max_results=None):
    """
    Raccoglie domande da Quantum Computing SE per una singola keyword di fase.
    Nessun tag necessario — il CONTESTO è implicito nel sito.
    Stack Exchange API non supporta OR in q — una chiamata per keyword.
    """
    url = f"{BASE_URL}/search/advanced"
    results = []
    page = 1

    while max_results is None or len(results) < max_results:
        params = {
            "site": SITE,
            "q": keyword,          # ricerca full-text nel body e titolo
            "filter": "withbody",
            "pagesize": 30,
            "page": page,
            "order": "desc",
            "sort": "activity"
        }
        if api_key:
            params["key"] = api_key

        data = make_request(url, params)
        if not data or not data.get("items"):
            break

        for item in data["items"]:
            thread = {
                # Metadati grezzi (schema metodologia)
                "url": item["link"],
                "fonte": "Quantum Computing Stack Exchange",
                "repository": f"site:{SITE}",
                "tipo": "Question",
                "fase_query": phase,
                "keyword_query": keyword,
                "titolo": item["title"],
                "data_creazione": datetime.fromtimestamp(item["creation_date"], tz=timezone.utc).isoformat(),
                "data_aggiornamento": datetime.fromtimestamp(item["last_activity_date"], tz=timezone.utc).isoformat(),
                "stato": "answered" if item.get("is_answered") else "open",
                "numero_commenti": item.get("answer_count", 0),
                "ruolo_autore": "apre il thread",
                "autore": item.get("owner", {}).get("display_name", "unknown"),
                "body": item.get("body", ""),
                "tags": item.get("tags", []),
                # Per coding iterativo (da compilare manualmente)
                "codice_COSA": None,
                "CHI": None,
                "QUANDO": None,
                "porzioni_codificate": []
            }
            results.append(thread)

        if not data.get("has_more"):
            break
        if max_results is not None and len(results) >= max_results:
            break

        page += 1
        time.sleep(1)  # pausa tra pagine

    return results[:max_results]


def collect_questions(phase, phase_terms, api_key=None, max_per_keyword=None):
    """
    Raccoglie domande per tutte le keyword di una fase.
    Una chiamata per keyword — i risultati vengono aggregati.
    """
    results = []
    for keyword in phase_terms:
        items = collect_questions_for_keyword(
            phase, keyword,
            api_key=api_key,
            max_results=max_per_keyword
        )
        results.extend(items)
        time.sleep(1)  # pausa tra keyword per non saturare la quota giornaliera
    return results


# ─── Deduplica ───

def deduplicate(threads):
    """Rimuove duplicati basandosi sull'URL."""
    seen = set()
    unique = []
    for t in threads:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)
    return unique


# ─── Main ───

def main(api_key, output_file, max_per_keyword=None):

    all_threads = []

    print("=== QUANTUM DEVOPS MINING — Quantum Computing Stack Exchange ===\n")
    print(f"Sito: {SITE}")
    print("Nota: CONTESTO implicito nel sito — keyword di fase usate direttamente\n")

    for phase, terms in PHASE_QUERIES.items():
        print(f"Fase: {phase} ({len(terms)} keyword)")

        questions = collect_questions(
            phase, terms,
            api_key=api_key,
            max_per_keyword=max_per_keyword
        )
        print(f"  Domande trovate (pre-dedup): {len(questions)}")
        all_threads.extend(questions)

        time.sleep(2)

    print()

    # Deduplica globale
    before = len(all_threads)
    all_threads = deduplicate(all_threads)
    after = len(all_threads)
    print(f"Totale thread: {before} → dopo deduplica: {after}")

    # Salva
    output = {
        "metadata": {
            "data_mining": datetime.now(tz=timezone.utc).isoformat(),
            "sito": SITE,
            "fasi": list(PHASE_QUERIES.keys()),
            "totale_thread": after,
            "note": "CONTESTO implicito nel sito — nessun tag usato"
        },
        "threads": all_threads
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDataset salvato in: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quantum DevOps Quantum Computing Stack Exchange Miner"
    )
    parser.add_argument("--key", default=None, help="Stack Exchange API Key (opzionale, aumenta quota)")
    parser.add_argument("--output", default="dataset_qcse.json")
    parser.add_argument("--max", type=int, default=None, help="Max thread per keyword (default: nessun limite, prende tutto)")
    args = parser.parse_args()

    api_key = args.key or os.getenv("STACKEXCHANGE_API_KEY")

    main(api_key, args.output, args.max)
