"""
gemini_reviewer.py — Gemini AI cross-reviewer for the scopus-auditor pipeline.

Sends a draft improvement plan to Gemini 2.0 Flash and returns structured
peer-review suggestions that Claude arbitrates before writing the final plan.

Usage:
  python gemini_reviewer.py "<draft text>" [--topic "<topic>"] [--model gemini-2.0-flash]
  python gemini_reviewer.py --stdin [--topic "<topic>"] [--model gemini-2.0-flash]

Output: JSON to stdout. Errors to stderr.
Requires: GEMINI_API_KEY env var.
"""

import argparse
import json
import os
import sys

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai", file=sys.stderr)
    sys.exit(1)

_REVIEW_PROMPT = """\
You are a senior academic peer reviewer with expertise in IEEE and Elsevier journals.
You have been given a draft improvement plan for a literature review.
Your task: critique this plan rigorously. Identify weak suggestions, missed issues,
structural problems, and gaps in coverage. Do NOT invent specific paper references.
If a reference would strengthen a point, flag the need without naming a paper.

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


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: GEMINI_API_KEY is not set.\n"
            "Fix: [System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'key', 'User')",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def review(draft: str, topic: str, model: str) -> None:
    api_key = _get_api_key()
    client = genai.Client(api_key=api_key)

    prompt = _REVIEW_PROMPT.format(topic=topic or "not specified", draft=draft)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
    except Exception as exc:
        print(f"ERROR: Gemini API call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    raw = response.text.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"ERROR: Gemini returned non-JSON response: {raw[:200]}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini peer-reviewer for scopus-auditor")
    parser.add_argument("draft", nargs="?", default=None, help="Draft plan text")
    parser.add_argument("--stdin", action="store_true", help="Read draft from stdin")
    parser.add_argument("--topic", default="", help="Research topic for context")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model ID")
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
