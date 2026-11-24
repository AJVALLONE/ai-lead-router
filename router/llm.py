"""Optional LLM pass: read free-text answers the rules can't, and adjust the score a little.

Guardrails:
- The model returns JSON only, validated against a fixed shape.
- Its adjustment is clamped to +/-15 points, so it can break ties but never override the rules.
- Any failure (no key, timeout, bad JSON) returns a zero adjustment. Routing never blocks on the LLM.
"""
import json
import os
import urllib.request

PROMPT = (
    "You review one inbound lead's free-text answer for buying intent. Respond with JSON only: "
    '{"adjustment": <integer -15..15>, "intent": "high"|"medium"|"low", "reason": "<12 words max>"}. '
    "Positive adjustment for urgency or a specific need, negative for joking, spam, or 'just curious'."
)
MAX_ADJ = 15


def assess(free_text, api_key=None, model=None):
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not free_text:
        return {"adjustment": 0, "intent": "unknown", "reason": "no LLM review"}
    body = json.dumps({
        "model": model or os.environ.get("ROUTER_MODEL", "claude-haiku-4-5"),
        "max_tokens": 120,
        "system": PROMPT,
        "messages": [{"role": "user", "content": free_text[:1000]}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            text = "".join(b.get("text", "") for b in json.load(r).get("content", []))
        return validate(json.loads(text))
    except Exception:
        return {"adjustment": 0, "intent": "unknown", "reason": "LLM unavailable"}


def validate(obj):
    adj = int(obj.get("adjustment", 0))
    intent = obj.get("intent") if obj.get("intent") in {"high", "medium", "low"} else "unknown"
    return {"adjustment": max(-MAX_ADJ, min(MAX_ADJ, adj)), "intent": intent,
            "reason": str(obj.get("reason", ""))[:120]}
