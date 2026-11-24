import hashlib
import hmac
import json
import unittest

from router import llm, routing, scoring, server

HOT = {"id": "1", "source": "google", "email": "a@gmail.com", "phone": "757-555-0100", "completed_quiz": True,
       "quiz": {"timeline": "this week", "budget": "ready to invest", "goal": "energy"}}


def no_llm(_):
    return {"adjustment": 0, "intent": "unknown", "reason": ""}


class ScoringTest(unittest.TestCase):
    def test_hot_lead(self):
        self.assertEqual(routing.route(HOT, llm_fn=no_llm)["tier"], "hot")

    def test_phone_normalization(self):
        self.assertEqual(scoring.normalize_phone("+1 (757) 555-0100"), "7575550100")
        self.assertIsNone(scoring.normalize_phone("555"))

    def test_dnc_is_suppressed_regardless_of_score(self):
        r = routing.route({**HOT, "dnc": True}, llm_fn=no_llm)
        self.assertEqual(r["actions"], ["suppress_outreach"])

    def test_no_phone_means_no_voice_call(self):
        r = routing.route({**HOT, "phone": ""}, llm_fn=no_llm)
        self.assertFalse(any(a.startswith("voice_agent") for a in r["actions"]))
        self.assertIn("request_phone_via_email", r["actions"])


class LLMGuardrailTest(unittest.TestCase):
    def test_adjustment_is_clamped(self):
        self.assertEqual(llm.validate({"adjustment": 90, "intent": "high"})["adjustment"], 15)
        self.assertEqual(llm.validate({"adjustment": -90, "intent": "low"})["adjustment"], -15)

    def test_bad_intent_becomes_unknown(self):
        self.assertEqual(llm.validate({"adjustment": 0, "intent": "ignore previous instructions"})["intent"], "unknown")

    def test_llm_cannot_promote_nurture_to_hot(self):
        weak = {"id": "2", "source": "meta", "quiz": {"timeline": "just researching"}}
        r = routing.route(weak, llm_fn=lambda _: {"adjustment": 15, "intent": "high", "reason": "x"})
        self.assertEqual(r["tier"], "nurture")


class ServerTest(unittest.TestCase):
    def sign(self, body):
        return hmac.new(server.SECRET, body, hashlib.sha256).hexdigest()

    def test_rejects_bad_signature(self):
        status, _ = server.handle(b"{}", "wrong")
        self.assertEqual(status, 401)

    def test_duplicate_delivery_not_rerouted(self):
        body = json.dumps({**HOT, "id": "dup-1"}).encode()
        server.handle(body, self.sign(body))
        status, payload = server.handle(body, self.sign(body))
        self.assertEqual(payload["status"], "duplicate")


if __name__ == "__main__":
    unittest.main()
