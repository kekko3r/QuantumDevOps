"""
Quantum DevOps Mining — GitHub Collector
Raccoglie Issues e Discussions dai repository GitHub
rilevanti per il dominio Quantum DevOps.

Metadati raccolti (per ogni thread):
- url, fonte, repository, titolo
- data creazione e aggiornamento
- stato, numero commenti
- ruolo autore (apre / risponde)

Uso:
    python github_collector.py --output dataset.json          # legge token da .env
    python github_collector.py --token YOUR_TOKEN --output dataset.json
"""

import requests
import json
import time
import argparse
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from queries import CONTEXT_TAGS, PHASE_QUERIES

load_dotenv()


# ─── Configurazione ───

BASE_URL = "https://api.github.com"
HEADERS = {}  # impostato dopo con il token

# Repository quantum rilevanti (il contesto è implicito)
# Aggiornati per coprire tutte le community identificate nella metodologia
TARGET_REPOS = [
    # Amazon Braket
    "amazon-braket/amazon-braket-sdk-python",  # SDK operativo, job submission, workflow ibridi
    # Qiskit / IBM Quantum
    "Qiskit/qiskit",
    "Qiskit/qiskit-ibm-runtime",        # deployment, job submission, backend
    "Qiskit/qiskit-aer",                # simulazione, fase TEST
    # PennyLane / Xanadu
    "PennyLaneAI/pennylane",
    # Cirq / Google
    "quantumlib/Cirq",
    # CUDA-Q / NVIDIA
    "NVIDIA/cuda-quantum",
    # Unitary Fund
    "unitaryfoundation/mitiq",          # error mitigation, fase TEST
    # Rigetti
    "rigetti/pyquil",                   # Rigetti Forest SDK, workflow ibridi
    # Microsoft Azure Quantum
    "microsoft/azure-quantum-python",   # Azure Quantum SDK, job submission
]

# Per repository quantum il blocco CONTESTO è implicito —
# usiamo solo le keyword di fase per le ricerche


# ─── Utility ───

def build_github_query(phase_terms, repo=None, max_terms=5):
    """
    Costruisce la query GitHub per una fase del ciclo.
    Su repository quantum il CONTESTO è implicito.
    max_terms: ridotto progressivamente in caso di errore 422.
    """
    terms = " OR ".join(f'"{t}"' for t in phase_terms[:max_terms])
    if repo:
        return f"({terms}) repo:{repo}"
    else:
        # Se non c'è repo specifico, aggiunge il contesto quantum
        context = " OR ".join(f'"{t}"' for t in CONTEXT_TAGS[:8])
        return f"({terms}) ({context})"


def rate_limit_wait(response):
    """Gestisce il rate limiting di GitHub."""
    remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
    if remaining < 5:
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        wait = max(0, reset_time - int(time.time())) + 5
        print(f"  Rate limit: aspetto {wait} secondi...")
        time.sleep(wait)


def make_request(url, params=None):
    """Esegue una richiesta GET con gestione errori e rate limit."""
    response = requests.get(url, headers=HEADERS, params=params)
    rate_limit_wait(response)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"  Errore {response.status_code}: {url}")
        return None


# ─── Raccolta Issues ───

def collect_issues(repo, phase, phase_terms, max_results=None):
    """
    Raccoglie Issues da un repository per una fase del ciclo.
    Restituisce lista di metadati normalizzati.
    In caso di errore 422 (query troppo lunga) riprova con meno keyword.
    """
    url = f"{BASE_URL}/search/issues"
    results = []
    page = 1

    # Retry progressivo: riduce le keyword finché la query non è valida
    query = None
    for max_terms in [5, 4, 3, 2, 1]:
        q = build_github_query(phase_terms, repo=repo, max_terms=max_terms)
        test_response = requests.get(
            url, headers=HEADERS,
            params={"q": f"{q} is:issue", "per_page": 1}
        )
        rate_limit_wait(test_response)
        if test_response.status_code == 200:
            query = q
            break
        elif test_response.status_code == 422:
            print(f"  Query con {max_terms} keyword troppo lunga, riprovo...")
            time.sleep(1)
            continue
        else:
            print(f"  Errore {test_response.status_code}: {url}")
            return []

    if query is None:
        print(f"  Impossibile costruire query valida per {repo} fase {phase}")
        return []

    params = {
        "q": f"{query} is:issue",
        "per_page": 30,
        "sort": "updated",
        "order": "desc"
    }

    while max_results is None or len(results) < max_results:
        params["page"] = page
        data = make_request(url, params)

        if not data or not data.get("items"):
            break

        for item in data["items"]:
            thread = {
                # Metadati grezzi (da schema metodologia)
                "url": item["html_url"],
                "fonte": "GitHub",
                "repository": repo,
                "tipo": "Issue",
                "fase_query": phase,
                "titolo": item["title"],
                "data_creazione": item["created_at"],
                "data_aggiornamento": item["updated_at"],
                "stato": item["state"],
                "numero_commenti": item["comments"],
                "ruolo_autore": "apre il thread",
                "autore": item["user"]["login"] if item.get("user") else "unknown",
                "body": item["body"] or "",
                # Per il coding iterativo (da compilare manualmente)
                "codice_COSA": None,
                "CHI": None,
                "QUANDO": None,
                "porzioni_codificate": []
            }
            results.append(thread)

        if len(data["items"]) < 30:
            break
        page += 1
        time.sleep(1)  # pausa tra pagine

    return results[:max_results]


def collect_discussions(repo, phase, phase_terms, max_results=None):
    """
    Raccoglie Discussions da un repository tramite GraphQL API.
    """
    terms_str = " OR ".join(phase_terms[:5])

    query = """
    query($query: String!, $cursor: String) {
      search(query: $query, type: DISCUSSION, first: 30, after: $cursor) {
        nodes {
          ... on Discussion {
            url
            title
            createdAt
            updatedAt
            comments { totalCount }
            author { login }
            body
            answer { body }
            category { name }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """

    variables = {
        "query": f"repo:{repo} {terms_str}",
        "cursor": None
    }

    results = []
    url = "https://api.github.com/graphql"

    while max_results is None or len(results) < max_results:
        response = requests.post(
            url,
            headers=HEADERS,
            json={"query": query, "variables": variables}
        )

        rate_limit_wait(response)

        if response.status_code != 200:
            print(f"  GraphQL errore {response.status_code}")
            break

        data = response.json()

        if "errors" in data:
            print(f"  GraphQL errori: {data['errors']}")
            break

        nodes = (data.get("data") or {}).get("search", {}).get("nodes", [])

        for item in nodes:
            if not item:
                continue
            thread = {
                "url": item["url"],
                "fonte": "GitHub",
                "repository": repo,
                "tipo": "Discussion",
                "fase_query": phase,
                "titolo": item["title"],
                "data_creazione": item["createdAt"],
                "data_aggiornamento": item["updatedAt"],
                "stato": "answered" if item.get("answer") else "open",
                "numero_commenti": item["comments"]["totalCount"],
                "ruolo_autore": "apre il thread",
                "autore": item["author"]["login"] if item.get("author") else "unknown",
                "body": item["body"] or "",
                "codice_COSA": None,
                "CHI": None,
                "QUANDO": None,
                "porzioni_codificate": []
            }
            results.append(thread)

        page_info = (data.get("data") or {}).get("search", {}).get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        if max_results is not None and len(results) >= max_results:
            break

        variables["cursor"] = page_info["endCursor"]
        time.sleep(1)

    return results[:max_results]


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

def main(token, output_file, max_per_query=None):
    global HEADERS
    HEADERS = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    all_threads = []

    print("=== QUANTUM DEVOPS MINING — GitHub ===\n")

    for repo in TARGET_REPOS:
        print(f"Repository: {repo}")

        for phase, terms in PHASE_QUERIES.items():
            print(f"  Fase: {phase} ({len(terms)} keyword)")

            # Issues
            issues = collect_issues(repo, phase, terms, max_results=max_per_query)
            print(f"    Issues trovate: {len(issues)}")
            all_threads.extend(issues)

            # Discussions
            discussions = collect_discussions(repo, phase, terms, max_results=max_per_query)
            print(f"    Discussions trovate: {len(discussions)}")
            all_threads.extend(discussions)

            time.sleep(2)  # pausa tra fasi

        print()

    # Deduplica
    before = len(all_threads)
    all_threads = deduplicate(all_threads)
    after = len(all_threads)
    print(f"Totale thread: {before} → dopo deduplica: {after}")

    # Salva
    output = {
        "metadata": {
            "data_mining": datetime.now(tz=timezone.utc).isoformat(),
            "fonti": TARGET_REPOS,
            "fasi": list(PHASE_QUERIES.keys()),
            "totale_thread": after
        },
        "threads": all_threads
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDataset salvato in: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum DevOps GitHub Miner")
    parser.add_argument("--token", default=None, help="GitHub Personal Access Token (default: GITHUB_PERSONAL_TOKEN)")
    parser.add_argument("--output", default="dataset_github.json", help="File di output")
    parser.add_argument("--max", type=int, default=None, help="Max thread per query (default: nessun limite, prende tutto)")
    args = parser.parse_args()

    token = args.token or os.getenv("GITHUB_PERSONAL_TOKEN")
    if not token:
        raise SystemExit("Errore: token GitHub non trovato. Passa --token o GITHUB_PERSONAL_TOKEN non impostato")

    main(token, args.output, args.max)