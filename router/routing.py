"""Turn a scored lead into CRM tags and next actions."""
from . import llm, scoring


def route(lead, llm_fn=llm.assess):
    if lead.get("dnc") or lead.get("sms_opt_out"):
        return {"tier": "suppressed", "score": 0, "tags": ["dnc"], "actions": ["suppress_outreach"],
                "reasons": ["do-not-contact flag"]}

    base, reasons = scoring.score(lead)
    review = llm_fn(lead.get("free_text"))
    final = max(0, min(100, base + review["adjustment"]))
    if review["adjustment"]:
        reasons.append(f"LLM {review['intent']} intent ({review['adjustment']:+}): {review['reason']}")
    t = scoring.tier(final)

    tags = [f"tier-{t}", f"src-{(lead.get('source') or 'unknown').lower()}"]
    profile = (lead.get("quiz") or {}).get("goal")
    if profile:
        tags.append(f"profile-{profile.lower().replace(' ', '-')}")

    actions = {
        "hot": ["voice_agent_call_now", "notify_sales_slack", "start_nurture_fast_track"],
        "warm": ["voice_agent_call_within_1h", "start_nurture_standard"],
        "nurture": ["start_nurture_30_day"],
    }[t]
    if not scoring.normalize_phone(lead.get("phone")):
        actions = [a for a in actions if not a.startswith("voice_agent")] + ["request_phone_via_email"]

    return {"tier": t, "score": final, "base_score": base, "tags": tags, "actions": actions, "reasons": reasons}
