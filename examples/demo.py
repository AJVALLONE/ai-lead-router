"""Route the example leads and print the decisions (no server, no API key needed)."""
import json
from pathlib import Path

from router.routing import route

for lead in json.loads(Path(__file__).with_name("leads.json").read_text()):
    r = route(lead)
    print(f"{lead['id']}: {r['tier']:<10} score={r['score']:<3} tags={r['tags']} actions={r['actions']}")
