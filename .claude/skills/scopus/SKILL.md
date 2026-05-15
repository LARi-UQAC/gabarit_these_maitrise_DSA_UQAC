---
name: scopus
description: "Use this skill to search Scopus for academic references, validate existing references, or produce literature reviews. Trigger on: /scopus, mentions of Scopus search, reference validation requests, finding papers on a topic."
---

# Scopus Skill

## Prerequisites

Before running any command, verify:

1. API key is set: `python -c "import os; print('OK' if os.environ.get('SCOPUS_API_KEY') else 'NOT SET')"`
2. `requests` is installed: `python -c "import requests; print('OK')"` — if missing, run `pip install requests`
3. Network: campus network or VPN active (Scopus blocks non-institutional IPs)

If the key is missing, ask the user to run:
```powershell
[System.Environment]::SetEnvironmentVariable("SCOPUS_API_KEY", "your-key", "User")
```
Then restart Claude Code for the variable to be visible.

---

## Mode Dispatch

Parse `$ARGUMENTS` to determine the mode, then run the script from the skill directory:

```powershell
cd ".claude/skills/scopus"
```

| If `$ARGUMENTS` starts with | Mode | Script call |
|---|---|---|
| `validate ` | Validate reference | `python scripts/scopus_api.py validate "<rest of args>"` |
| `cite ` | Full metadata by DOI | `python scripts/scopus_api.py cite "<DOI>"` |
| `author ` | Author profile | `python scripts/scopus_api.py author "<name>"` |
| `review ` | Literature review | `python scripts/scopus_api.py search "<rest>" --count 15` then synthesize |
| anything else | Search | `python scripts/scopus_api.py search "<all args>" --count 10` |

---

## Output Formatting

### Search results

Present as a numbered list:

```
[1] Title. Author et al. (Year). Journal. DOI: https://doi.org/... — N citations
[2] ...
```

### Validate

Report `✓ Found` or `✗ Not found`, then show the full metadata block (title, authors, journal, year, DOI, citations).

### Review mode

1. Run search with `--count 15`
2. For each paper that has a DOI, run `cite` to retrieve the full abstract
3. Identify 3–5 themes across the papers
4. Write 3–5 sentences per theme, citing papers with `[N]`
5. Append a numbered reference list
6. Append a BibTeX block ready to paste into LaTeX

### Author

Show: full name, affiliation, h-index, document count, top 5 papers by citation.

---

## Error Handling

| Error | Action |
|---|---|
| `401 Unauthorized` | API key invalid — ask user to verify `SCOPUS_API_KEY` |
| `403 Forbidden` | Not on institution network — ask user to connect to UQAC VPN or provide `--insttoken` |
| `429 Too Many Requests` | Rate limit hit — wait 60 s and retry once |
| `requests` module missing | Run `pip install requests` then retry |
| No results returned | Broaden search terms; suggest alternative Scopus query keywords |

For off-campus access without VPN, append `--insttoken <token>` to any script call.
