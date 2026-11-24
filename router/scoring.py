"""Deterministic lead scoring. The LLM can adjust this score, but only within a bounded range."""
import re

INTENT_ANSWERS = {
    # quiz answer -> points; tuned per funnel
    "timeline": {"this week": 25, "this month": 15, "just researching": 0},
    "budget": {"ready to invest": 20, "depends on price": 8, "not sure": 0},
    "goal": {"energy": 8, "sleep": 8, "weight": 8, "active lifestyle": 8},
}
SOURCE_POINTS = {"meta": 5, "google": 10, "referral": 15, "organic": 8}
PHONE_RE = re.compile(r"^\+?1?\d{10}$")


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) >= 10 else None


def score(lead):
    """Return (score 0-100, reasons[]) from structured fields only."""
    pts, reasons = 0, []
    answers = {k.lower(): str(v).lower() for k, v in (lead.get("quiz") or {}).items()}
    for field, table in INTENT_ANSWERS.items():
        ans = answers.get(field)
        if ans in table and table[ans]:
            pts += table[ans]
            reasons.append(f"{field}={ans} (+{table[ans]})")
    src = (lead.get("source") or "").lower()
    if src in SOURCE_POINTS:
        pts += SOURCE_POINTS[src]
        reasons.append(f"source={src} (+{SOURCE_POINTS[src]})")
    if normalize_phone(lead.get("phone")):
        pts += 15
        reasons.append("valid phone (+15)")
    if lead.get("email") and "@" in lead["email"] and not lead["email"].endswith(("@test.com", "@example.com")):
        pts += 10
        reasons.append("valid email (+10)")
    if lead.get("completed_quiz"):
        pts += 10
        reasons.append("completed quiz (+10)")
    return min(pts, 100), reasons


def tier(points):
    if points >= 70:
        return "hot"
    if points >= 40:
        return "warm"
    return "nurture"
