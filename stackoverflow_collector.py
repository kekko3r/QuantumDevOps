"""
Quantum DevOps Mining — Stack Overflow Collector
Raccoglie domande e risposte da Stack Overflow
rilevanti per il dominio Quantum DevOps.

Su Stack Overflow il CONTESTO è garantito dai tag quantum.
Le keyword di fase vengono usate per ricerca full-text (campo q).
Una chiamata per keyword per rispettare la sintassi dell'API.

Uso:
    python stackoverflow_collector.py --output dataset_so.json
    python stackoverflow_collector.py --key YOUR_KEY --output dataset_so.json
"""

import requests
import json
import time
import argparse
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from queries import PHASE_QUERIES, CONTEXT_TAGS, CONTEXT_FREETEXT

load_dotenv()

# ─── Configurazione ───

BASE_URL = "https://api.stackexchange.com/2.3"

# Tag quantum rilevanti su Stack Overflow — da CONTEXT_TAGS (tool/community
# con un tag verosimilmente reale). I concetti senza tag (CONTEXT_FREETEXT)
# vengono cercati separatamente come testo libero, senza filtro tag.
QUANTUM_TAGS = [t.replace(" ", "-") for t in CONTEXT_TAGS]


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

def collect_questions_for_keyword(tag, phase, keyword, api_key=None, max_results=30):
    """
    Raccoglie domande da Stack Overflow per un singolo tag + keyword.
    Stack Exchange API non supporta OR in intitle/q — una chiamata per keyword.
    """
    url = f"{BASE_URL}/search/advanced"
    results = []
    page = 1

    while len(results) < max_results:
        params = {
            "site": "stackoverflow",
            "tagged": tag,
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
                "fonte": "Stack Overflow",
                "repository": f"tag:{tag}",
                "tipo": "Question",
                "fase_query": phase,
                "keyword_query": keyword,   # keyword specifica che ha trovato questo thread
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

        if not data.get("has_more") or len(results) >= max_results:
            break

        page += 1
        time.sleep(1)

    return results[:max_results]


def collect_questions(tag, phase, phase_terms, api_key=None, max_per_keyword=10):
    """
    Raccoglie domande per tutte le keyword di una fase.
    Una chiamata per keyword — i risultati vengono aggregati.
    """
    results = []
    for keyword in phase_terms:
        items = collect_questions_for_keyword(
            tag, phase, keyword,
            api_key=api_key,
            max_results=max_per_keyword
        )
        results.extend(items)
        time.sleep(1)  # pausa tra keyword per non saturare la quota giornaliera
    return results


def collect_questions_for_keyword_freetext(context_term, phase, keyword, api_key=None, max_results=30):
    """
    Raccoglie domande per un concetto ibrido senza tag dedicato (CONTEXT_FREETEXT).
    Nessun filtro tagged= — una chiamata per (context_term, keyword), ancorata
    dalla parola "quantum" per evitare rumore su termini generici come "hybrid".
    """
    url = f"{BASE_URL}/search/advanced"
    results = []
    page = 1

    while len(results) < max_results:
        params = {
            "site": "stackoverflow",
            "q": f"{keyword} quantum {context_term}",
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
                "url": item["link"],
                "fonte": "Stack Overflow",
                "repository": f"context:{context_term}",
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
                "codice_COSA": None,
                "CHI": None,
                "QUANDO": None,
                "porzioni_codificate": []
            }
            results.append(thread)

        if not data.get("has_more") or len(results) >= max_results:
            break

        page += 1
        time.sleep(1)

    return results[:max_results]


def collect_questions_freetext(context_term, phase, phase_terms, api_key=None, max_per_keyword=10):
    """
    Raccoglie domande su un concetto ibrido senza tag, per tutte le keyword di una fase.
    """
    results = []
    for keyword in phase_terms:
        items = collect_questions_for_keyword_freetext(
            context_term, phase, keyword,
            api_key=api_key,
            max_results=max_per_keyword
        )
        results.extend(items)
        time.sleep(1)
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

def main(api_key, output_file, max_per_keyword=10):

    all_threads = []

    print("=== QUANTUM DEVOPS MINING — Stack Overflow ===\n")

    for tag in QUANTUM_TAGS:
        print(f"Tag: {tag}")

        for phase, terms in PHASE_QUERIES.items():
            print(f"  Fase: {phase} ({len(terms)} keyword)")

            questions = collect_questions(
                tag, phase, terms,
                api_key=api_key,
                max_per_keyword=max_per_keyword
            )
            print(f"    Domande trovate (pre-dedup): {len(questions)}")
            all_threads.extend(questions)

            time.sleep(2)

        print()

    # Ricerca aggiuntiva: concetti ibridi senza tag dedicato (CONTEXT_FREETEXT)
    print("Contesto: ricerca freetext (concetti senza tag dedicato)")
    for context_term in CONTEXT_FREETEXT:
        print(f"Termine contesto: {context_term}")

        for phase, terms in PHASE_QUERIES.items():
            print(f"  Fase: {phase} ({len(terms)} keyword)")

            questions = collect_questions_freetext(
                context_term, phase, terms,
                api_key=api_key,
                max_per_keyword=max_per_keyword
            )
            print(f"    Domande trovate (pre-dedup): {len(questions)}")
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
            "tag_usati": QUANTUM_TAGS,
            "contesto_freetext": CONTEXT_FREETEXT,
            "fasi": list(PHASE_QUERIES.keys()),
            "totale_thread": after
        },
        "threads": all_threads
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDataset salvato in: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum DevOps Stack Overflow Miner")
    parser.add_argument("--key", default=None, help="Stack Exchange API Key (opzionale, aumenta quota)")
    parser.add_argument("--output", default="dataset_stackoverflow.json")
    parser.add_argument("--max", type=int, default=10, help="Max thread per keyword per tag")
    args = parser.parse_args()

    api_key = args.key or os.getenv("STACKEXCHANGE_API_KEY")

    main(api_key, args.output, args.max)
