"""
github_reviewer.py — GitHub Copilot (GPT-4o via GitHub Models) cross-reviewer
for the scopus-auditor pipeline.

Sends a draft improvement plan to GPT-4o via the GitHub Models API and returns
structured peer-review suggestions that Claude arbitrates before writing the final plan.

Usage:
  python github_reviewer.py "<draft text>" [--topic "<topic>"] [--model gpt-4o]
  python github_reviewer.py --stdin [--topic "<topic>"] [--model gpt-4o]

Output: JSON to stdout. Errors to stderr.
Requires: GITHUB_TOKEN env var (GitHub personal access token with Education Pro).
"""

import argparse
import json
import os
import sys

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai not installed. Run: pip install openai", file=sys.stderr)
    sys.exit(1)

_GITHUB_MODELS_ENDPOINT = "https://models.inference.ai.azure.com"

_SYSTEM_PROMPT = (
    "You are a senior academic peer reviewer with expertise in IEEE and Elsevier journals. "
    "Critique the provided improvement plan rigorously. Identify weak suggestions, missed issues, "
    "structural problems, and coverage gaps. Do NOT invent specific paper references. "
    "If a reference would strengthen a point, flag the need without naming a paper. "
    "Respond ONLY with valid JSON — no prose, no markdown wrapping."
)

_USER_PROMPT = """\
Respond ONLY with valid JSON matching this exact schema:
{{
  "overall_assessment": "<2-3 sentence global critique of the plan quality>",
  "suggestions": [
    {{
      "target_section": "<section id like A1, B2, C, E, or general>",
      "type": "<text_improvement | reference_issue | coverage_gap | style | structure>",
      "suggestion": "<specific actionable text>",
      "confidence": "<high | medium | low>",
      "requires_scopus_validation": <true | false>
    }}
  ]
}}

Topic context: {topic}

Draft improvement plan:
---
{draft}
---
"""


def _get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print(
            "ERROR: GITHUB_TOKEN is not set.\n"
            "Fix: [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_...', 'User')",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def review(draft: str, topic: str, model: str) -> None:
    token = _get_token()
    client = OpenAI(base_url=_GITHUB_MODELS_ENDPOINT, api_key=token)

    user_message = _USER_PROMPT.format(topic=topic or "not specified", draft=draft)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
    except Exception as exc:
        print(f"ERROR: GitHub Models API call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    raw = response.choices[0].message.content.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"ERROR: GitHub Models returned non-JSON response: {raw[:200]}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Copilot peer-reviewer for scopus-auditor")
    parser.add_argument("draft", nargs="?", default=None, help="Draft plan text")
    parser.add_argument("--stdin", action="store_true", help="Read draft from stdin")
    parser.add_argument("--topic", default="", help="Research topic for context")
    parser.add_argument("--model", default="gpt-4o", help="GitHub Models model ID")
    args = parser.parse_args()

    if args.stdin:
        draft = sys.stdin.read().strip()
    elif args.draft:
        draft = args.draft.strip()
    else:
        parser.error("Provide draft text as argument or use --stdin")

    if not draft:
        print("ERROR: Draft text is empty.", file=sys.stderr)
        sys.exit(1)

    review(draft, args.topic, args.model)


if __name__ == "__main__":
    main()
