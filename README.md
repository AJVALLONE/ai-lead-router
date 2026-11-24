# AI Lead Router

Score, tag, and route inbound funnel leads the moment they arrive, then hand the hot ones to an AI voice agent for an immediate call. An LLM reads the free-text answers the rules can't, but it is kept on a short leash so it can never override the scoring logic.

This is a public reference version of the lead-handling layer behind a quiz funnel I launched in November 2026, where an AI voice agent reached 82% of new leads in the first 11 days. The production version runs on GoHighLevel webhooks and tags; this one is standalone, dependency-free Python so the logic is easy to read and test.

![deps](https://img.shields.io/badge/dependencies-zero-brightgreen) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

## The problem it solves

Speed to lead decides most funnels. Before: leads sat in a CRM until someone reviewed them, and everyone got the same follow-up. After: every lead is scored, tagged by profile, and routed within seconds. Hot leads get a call now, warm leads within the hour, and the rest go into a 30-day nurture. Do-not-contact requests are suppressed before anything else runs.

## How it decides

```
funnel webhook (signed)
        │
        ▼
 server.py   ── verify HMAC signature, ignore duplicate deliveries
        │
        ▼
 scoring.py  ── deterministic points: quiz intent, budget, source, valid phone/email
        │
        ▼
 llm.py      ── optional: reads free text, returns JSON {adjustment, intent, reason}
        │          clamped to ±15 points; any failure = 0 adjustment
        ▼
 routing.py  ── tier (hot / warm / nurture / suppressed) → CRM tags + next actions
```

### Guardrails on the LLM

The LLM is useful for one thing rules can't do: reading "I've been exhausted for months and want to start ASAP" versus "lol just clicking around." It is not trusted with anything else.

- **Bounded influence:** its adjustment is clamped to ±15 points, so it can break ties but can't turn a cold lead into a hot one (there's a test for exactly that).
- **Validated output:** JSON only, fixed fields, unknown values discarded. Prompt-injection text in a lead becomes `intent: unknown`.
- **Never blocking:** no key, a timeout, or bad JSON means a zero adjustment. Routing still completes.
- **Compliance first:** do-not-contact and opt-out flags short-circuit everything. No phone number means no voice call.

## Run it

```bash
git clone https://github.com/AJVALLONE/ai-lead-router
cd ai-lead-router
python -m examples.demo                      # route 4 sample leads, no key needed
python -m unittest discover -s tests -v      # 9 tests
python -m router.server                      # webhook on :8080/webhook/lead
```

Sample output:

```
L-1001: hot        score=93  actions=['voice_agent_call_now', 'notify_sales_slack', 'start_nurture_fast_track']
L-1002: warm       score=61  actions=['start_nurture_standard', 'request_phone_via_email']
L-1003: nurture    score=5   actions=['start_nurture_30_day', 'request_phone_via_email']
L-1004: suppressed score=0   actions=['suppress_outreach']
```

Set `ANTHROPIC_API_KEY` to turn on the free-text review (defaults to a small, fast model; it only needs to read one answer).

## Adapting it

Scoring weights live in one table in `scoring.py`, so a marketer can tune them without touching routing logic. Tiers map to actions in one dictionary in `routing.py`. In production those actions become CRM tags that trigger the voice agent, Slack alerts, and nurture workflows.

## Author

Anthony Vallone, growth leader who builds his own tooling. [LinkedIn](https://linkedin.com/in/ajvallone) · [Portfolio](https://anthonyvallone.netlify.app)
