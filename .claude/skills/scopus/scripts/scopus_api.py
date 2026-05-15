"""
scopus_api.py — Scopus REST API client for the Claude Code /scopus skill.

Usage:
  python scopus_api.py search "<query>" [--count N] [--insttoken TOKEN]
  python scopus_api.py cite "<DOI>"     [--insttoken TOKEN]
  python scopus_api.py validate "<DOI or title>" [--insttoken TOKEN]
  python scopus_api.py author "<name>"  [--insttoken TOKEN]
  python scopus_api.py journal "<journal name or ISSN>" [--insttoken TOKEN]

Output: JSON to stdout. Errors to stderr with actionable messages.

Requires: SCOPUS_API_KEY env var (set via Windows User environment variables).
          On-campus network or UQAC VPN (or --insttoken for off-campus access).
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
ABSTRACT_URL = "https://api.elsevier.com/content/abstract/doi/{doi}"
AUTHOR_SEARCH_URL = "https://api.elsevier.com/content/search/author"
SERIAL_TITLE_URL = "https://api.elsevier.com/content/serial/title"


def _get_api_key() -> str:
    key = os.environ.get("SCOPUS_API_KEY", "").strip()
    if not key:
        fallback = os.path.join(os.path.dirname(__file__), "..", ".scopus_key")
        if os.path.exists(fallback):
            with open(fallback) as f:
                key = f.read().strip()
    if not key:
        print(
            "ERROR: SCOPUS_API_KEY is not set.\n"
            "Fix: run in PowerShell:\n"
            "  [System.Environment]::SetEnvironmentVariable('SCOPUS_API_KEY', 'your-key', 'User')\n"
            "Then restart Claude Code.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _make_headers(api_key: str, insttoken: str | None = None) -> dict:
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    if insttoken:
        headers["X-ELS-Insttoken"] = insttoken
    return headers


def _check_response(response: requests.Response) -> None:
    if response.status_code == 401:
        print("ERROR 401: Invalid API key. Verify SCOPUS_API_KEY.", file=sys.stderr)
        sys.exit(1)
    if response.status_code == 403:
        print(
            "ERROR 403: Access denied. Connect to UQAC VPN or provide --insttoken.",
            file=sys.stderr,
        )
        sys.exit(1)
    if response.status_code == 429:
        print("ERROR 429: Rate limit exceeded. Wait 60 seconds and retry.", file=sys.stderr)
        sys.exit(1)
    if response.status_code != 200:
        print(f"ERROR {response.status_code}: {response.text[:300]}", file=sys.stderr)
        sys.exit(1)


def _search(query: str, count: int, api_key: str, insttoken: str | None) -> None:
    params = {
        "query": query,
        "count": count,
        "field": (
            "dc:title,dc:creator,prism:publicationName,prism:coverDate,"
            "prism:doi,citedby-count,dc:description"
        ),
    }
    resp = requests.get(
        SEARCH_URL, headers=_make_headers(api_key, insttoken), params=params, timeout=30
    )
    _check_response(resp)

    entries = resp.json().get("search-results", {}).get("entry", [])
    results = [
        {
            "title": e.get("dc:title", ""),
            "authors": e.get("dc:creator", ""),
            "journal": e.get("prism:publicationName", ""),
            "year": (e.get("prism:coverDate") or "")[:4],
            "doi": e.get("prism:doi", ""),
            "citations": e.get("citedby-count", "0"),
            "abstract": e.get("dc:description", ""),
        }
        for e in entries
    ]
    print(json.dumps({"mode": "search", "query": query, "count": len(results), "results": results}, ensure_ascii=False, indent=2))


def _cite(doi: str, api_key: str, insttoken: str | None) -> None:
    url = ABSTRACT_URL.format(doi=doi.strip())
    params = {
        "field": (
            "dc:title,dc:creator,prism:publicationName,prism:coverDate,"
            "prism:doi,citedby-count,dc:description,prism:issn,authkeywords,affiliation"
        )
    }
    resp = requests.get(
        url, headers=_make_headers(api_key, insttoken), params=params, timeout=30
    )
    _check_response(resp)

    data = resp.json().get("abstracts-retrieval-response", {})
    core = data.get("coredata", {})

    raw_authors = data.get("authors", {}).get("author", [])
    if isinstance(raw_authors, dict):
        raw_authors = [raw_authors]
    authors = [
        f"{a.get('ce:surname', '')}, {a.get('ce:given-name', '')}"
        for a in raw_authors
    ]

    keywords = data.get("authkeywords", {}).get("author-keyword", [])
    if isinstance(keywords, dict):
        keywords = [keywords]
    keyword_list = [k.get("$", "") for k in keywords if isinstance(k, dict)]

    print(json.dumps({
        "mode": "cite",
        "doi": doi,
        "title": core.get("dc:title", ""),
        "authors": authors,
        "journal": core.get("prism:publicationName", ""),
        "year": (core.get("prism:coverDate") or "")[:4],
        "citations": core.get("citedby-count", "0"),
        "abstract": core.get("dc:description", ""),
        "keywords": keyword_list,
        "issn": core.get("prism:issn", ""),
    }, ensure_ascii=False, indent=2))


def _validate(ref: str, api_key: str, insttoken: str | None) -> None:
    # DOI lookup takes priority
    if ref.startswith("10."):
        _cite(ref, api_key, insttoken)
        return

    params = {
        "query": f"TITLE({ref})",
        "count": 5,
        "field": "dc:title,dc:creator,prism:publicationName,prism:coverDate,prism:doi,citedby-count",
    }
    resp = requests.get(
        SEARCH_URL, headers=_make_headers(api_key, insttoken), params=params, timeout=30
    )
    _check_response(resp)

    data = resp.json().get("search-results", {})
    total = int(data.get("opensearch:totalResults", 0))
    entries = data.get("entry", [])
    results = [
        {
            "title": e.get("dc:title", ""),
            "authors": e.get("dc:creator", ""),
            "journal": e.get("prism:publicationName", ""),
            "year": (e.get("prism:coverDate") or "")[:4],
            "doi": e.get("prism:doi", ""),
            "citations": e.get("citedby-count", "0"),
        }
        for e in entries
    ]
    print(json.dumps({
        "mode": "validate",
        "query": ref,
        "total_found": total,
        "results": results,
    }, ensure_ascii=False, indent=2))


def _journal(name: str, api_key: str, insttoken: str | None) -> None:
    params = {
        "title": name,
        "field": "Title,ISSN,SJRList,CiteScoreYearInfoList,SubjectArea,Publisher,SNIPList",
        "count": 3,
    }
    resp = requests.get(
        SERIAL_TITLE_URL, headers=_make_headers(api_key, insttoken), params=params, timeout=30
    )
    _check_response(resp)

    data = resp.json().get("serial-metadata-response", {})
    entries = data.get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]

    results = []
    for e in entries:
        sjr_list = e.get("SJRList", {}).get("SJR", [])
        if isinstance(sjr_list, dict):
            sjr_list = [sjr_list]
        sjr_value = sjr_list[0].get("$", "") if sjr_list else ""

        # CiteScore from most recent Complete year
        cite_score = ""
        cs_years = e.get("CiteScoreYearInfoList", {}).get("CiteScoreYearInfo", [])
        if isinstance(cs_years, dict):
            cs_years = [cs_years]
        for cs in cs_years:
            if cs.get("@status") == "Complete":
                cs_infos = cs.get("CiteScoreInformationList", {}).get("CiteScoreInfo", [])
                if isinstance(cs_infos, dict):
                    cs_infos = [cs_infos]
                if cs_infos:
                    cite_score = cs_infos[0].get("CiteScore", "")
                break

        # Subject areas with quartile when available
        subject_areas = e.get("SubjectArea", [])
        if isinstance(subject_areas, dict):
            subject_areas = [subject_areas]
        areas = []
        for sa in subject_areas[:4]:
            abbrev = sa.get("@abbrevName", "")
            code = sa.get("@code", "")
            areas.append(f"{abbrev} ({code})" if code else abbrev)

        results.append({
            "title": e.get("dc:title", ""),
            "issn": e.get("prism:issn", ""),
            "publisher": e.get("dc:publisher", ""),
            "sjr": sjr_value,
            "cite_score": cite_score,
            "subject_areas": areas,
        })

    print(json.dumps({
        "mode": "journal",
        "query": name,
        "results": results,
    }, ensure_ascii=False, indent=2))


def _author(name: str, api_key: str, insttoken: str | None) -> None:
    parts = name.split()
    if len(parts) >= 2:
        query = f"AUTHLASTNAME({parts[-1]}) AND AUTHFIRST({parts[0][0]})"
    else:
        query = f"AUTHLASTNAME({name})"

    params = {
        "query": query,
        "count": 5,
        "field": "dc:identifier,preferred-name,affiliation-current,document-count,h-index,coauthor-count",
    }
    resp = requests.get(
        AUTHOR_SEARCH_URL, headers=_make_headers(api_key, insttoken), params=params, timeout=30
    )
    _check_response(resp)

    entries = resp.json().get("search-results", {}).get("entry", [])
    results = []
    for e in entries:
        pn = e.get("preferred-name", {})
        aff = e.get("affiliation-current", {})
        results.append({
            "name": f"{pn.get('surname', '')}, {pn.get('given-name', '')}",
            "affiliation": aff.get("affiliation-name", "") if isinstance(aff, dict) else "",
            "documents": e.get("document-count", ""),
            "h_index": e.get("h-index", ""),
            "coauthors": e.get("coauthor-count", ""),
            "author_id": e.get("dc:identifier", "").replace("AUTHOR_ID:", ""),
        })
    print(json.dumps({"mode": "author", "query": name, "results": results}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scopus REST API client for Claude Code")
    parser.add_argument("mode", choices=["search", "cite", "validate", "author", "journal"])
    parser.add_argument("query", help="Search query, DOI, title fragment, or author name")
    parser.add_argument("--count", type=int, default=10, help="Max results (search mode only)")
    parser.add_argument("--insttoken", default=None, help="Institution token for off-campus access")
    args = parser.parse_args()

    api_key = _get_api_key()

    dispatch = {
        "search": lambda: _search(args.query, args.count, api_key, args.insttoken),
        "cite": lambda: _cite(args.query, api_key, args.insttoken),
        "validate": lambda: _validate(args.query, api_key, args.insttoken),
        "author": lambda: _author(args.query, api_key, args.insttoken),
        "journal": lambda: _journal(args.query, api_key, args.insttoken),
    }
    dispatch[args.mode]()


if __name__ == "__main__":
    main()
