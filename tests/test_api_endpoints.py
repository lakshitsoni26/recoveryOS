"""
E2E & Unit Test Suite for FastAPI RecoveryOS Server and Engine.
"""
import unittest
from fastapi.testclient import TestClient
from api.server import app, payment_ledger


class TestRecoveryAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "Razorpay RecoveryOS Engine")
        self.assertIn("gateway_mode", data)
        self.assertIn("sarvam_tts_ready", data)
        self.assertIn("sarvam_tts_active", data)
        self.assertIn("active_campaign", data)

    def test_get_personas(self):
        resp = self.client.get("/api/personas")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_records"], 50)
        self.assertEqual(len(data["records"]), 50)
        self.assertIn("willing_forgetful", data["distribution"])

    def test_simulate_turn_agree_to_pay(self):
        payload = {
            "customer_id": "CUST_TEST_01",
            "customer_name": "Aarav Sharma",
            "amount_due": 3000,
            "days_overdue": 10,
            "customer_utterance": "Haan bhai link bhej do abhi pay karta hoon",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["turn"], 1)
        self.assertEqual(data["detected_intent"], "agree_to_pay")
        self.assertEqual(data["sentiment"], "Cooperative (Positive)")
        self.assertIsNotNone(data["payment_link"])
        self.assertIn("rzp.io", data["payment_link"]["short_url"])
        self.assertEqual(data["payment_link"]["amount_inr"], 3000.0)
        self.assertIn(data["payment_link"]["payment_link_id"], payment_ledger)

    def test_simulate_turn_dispute_charge(self):
        payload = {
            "customer_id": "CUST_TEST_02",
            "customer_name": "Meera Patel",
            "amount_due": 5000,
            "days_overdue": 15,
            "customer_utterance": "Yeh galat charge hai, maine already paid kar diya hai fraud mat karo",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_intent"], "dispute_charge")
        self.assertEqual(data["sentiment"], "Concerned (Disputed)")
        self.assertTrue(data["stopping_rule_triggered"])
        self.assertEqual(data["state"], "DISPUTE_HALTED")
        self.assertIsNone(data["payment_link"])
        self.assertIn("DISP-", data["agent_response"])

    def test_simulate_turn_reschedule(self):
        payload = {
            "customer_id": "CUST_TEST_03",
            "customer_name": "Karan Malhotra",
            "amount_due": 8000,
            "days_overdue": 20,
            "customer_utterance": "Abhi salary nahi aayi, friday ko time de do",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_intent"], "reschedule_request")
        self.assertEqual(data["sentiment"], "Negotiating (Neutral)")
        self.assertEqual(data["state"], "RESCHEDULED")

    def test_simulate_turn_ghost(self):
        payload = {
            "customer_id": "CUST_TEST_04",
            "customer_name": "Silent User",
            "amount_due": 1500,
            "days_overdue": 5,
            "customer_utterance": "...",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_intent"], "ghost_no_response")
        self.assertEqual(data["sentiment"], "Unresponsive (Silent)")
        self.assertTrue(data["stopping_rule_triggered"])
        self.assertEqual(data["state"], "GHOST_STOPPED")

    def test_simulate_turn_partial_pay(self):
        payload = {
            "customer_id": "CUST_TEST_05",
            "customer_name": "Sunil Varma",
            "amount_due": 6000,
            "days_overdue": 14,
            "customer_utterance": "Main abhi 50% partial payment kar sakta hoon",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_intent"], "partial_payment_offer")
        self.assertEqual(data["sentiment"], "Cooperative (Positive)")
        self.assertIsNotNone(data["payment_link"])
        self.assertEqual(data["payment_link"]["amount_inr"], 3000.0)

    def test_get_campaign_metrics(self):
        resp = self.client.get("/api/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        summary = data["summary"]
        self.assertEqual(summary["total_accounts"], 50)
        self.assertEqual(summary["total_delinquent_book_inr"], 406700)
        self.assertEqual(summary["simulated_recovered_inr"], 221700)
        self.assertEqual(summary["disputes_halted_count"], 10)
        self.assertEqual(summary["ghosts_halted_count"], 8)
        
        funnel = data["funnel"]
        self.assertEqual(funnel["stage_1_contacted"]["accounts"], 50)
        self.assertEqual(funnel["stage_2_commitment"]["accounts"], 28)
        self.assertEqual(funnel["stage_3_link_issued"]["accounts"], 18)
        self.assertEqual(funnel["stage_4_recovered_simulated"]["accounts"], 28)
        self.assertEqual(funnel["stage_4_recovered_simulated"]["amount_inr"], 221700)

    def test_custom_persona(self):
        payload = {
            "name": "Ananya Roy",
            "amount_due": 12500,
            "days_overdue": 30,
            "persona_type": "willing_forgetful",
            "opening_reply": "Sending right now via UPI"
        }
        resp = self.client.post("/api/custom-persona", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["customer"]["name"], "Ananya Roy")
        self.assertEqual(data["customer"]["amount"], 12500)

    def test_webhook_payment_captured(self):
        # Create a payment link first
        link_resp = self.client.post("/api/simulate-turn", json={
            "customer_id": "CUST_WH_01",
            "customer_name": "Webhook Tester",
            "amount_due": 2000,
            "customer_utterance": "bhej do link payment karta hoon",
            "turn_number": 1
        })
        link_id = link_resp.json()["payment_link"]["payment_link_id"]

        # Trigger webhook
        wh_payload = {
            "payment_link_id": link_id,
            "customer_id": "CUST_WH_01",
            "amount_inr": 2000,
            "payment_method": "upi"
        }
        wh_resp = self.client.post("/api/webhook/payment-captured", json=wh_payload)
        self.assertEqual(wh_resp.status_code, 200)
        wh_data = wh_resp.json()
        self.assertEqual(wh_data["event"], "payment_link.paid")
        self.assertEqual(wh_data["payload"]["status"], "paid")
        self.assertIn("UTR_RZP_", wh_data["payload"]["utr_number"])
        self.assertEqual(payment_ledger[link_id]["status"], "paid_and_captured")

    def test_trigger_batch_run(self):
        resp = self.client.post("/api/run-batch?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("funnel", data)
        self.assertIn("records", data)
        self.assertEqual(data["funnel"]["stage_1_contacted"]["count"], 5)


if __name__ == "__main__":
    unittest.main()
