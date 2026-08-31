"""
E2E Multi-Tier Test Suite for Razorpay RecoveryOS (Buildathon Track 3).
Opaque-box verification across Tiers 1-4 mapped to TEST_INFRA.md and PROJECT.md.

Tier 1: Feature Coverage (All individual API endpoints & core modules)
Tier 2: Boundary & Corner Cases (Empty strings, massive amounts, missing fields, special characters, error conditions)
Tier 3: Cross-Feature State Machine Combinations (Simulate -> Payment Link -> Webhook Captured -> Ledger Updated -> Funnel)
Tier 4: Real-World Workload Testing (50-record batch evaluation, ₹2,21,700 recovery score, cryptographic SHA256 audit integrity)
"""

import os
import sys
import json
import hashlib
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from api.server import app, payment_ledger, custom_personas
from agent.intent_classifier import HinglishIntentClassifier
from agent.negotiation_engine import RecoveryNegotiationEngine, RecoveryState
from integrations.razorpay_client import RazorpayRecoveryClient
from audio.sarvam_client import SarvamAudioClient
from eval.funnel_scorer import FunnelScorer
from eval.audit_logger import AuditLogger
from eval.batch_runner import run_batch_evaluation
from data.persona_bank.schemas import PersonaBank, CustomerRecord, ScoringCriteria


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Feature Coverage Verification.
    Verifies all individual API endpoints, schemas, audio contracts, and frontend build artifacts.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.bank_path = WORKSPACE_ROOT / "data" / "persona_bank" / "personas.json"

    def test_01_health_check_endpoint(self):
        """Feature 1: GET /api/health returns 200 with service details and gateway mode."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200, f"Health endpoint failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("Razorpay RecoveryOS", data.get("service", ""))
        self.assertIn("gateway_mode", data)
        self.assertIn("active_campaign", data)
        self.assertIsInstance(data.get("sarvam_tts_ready"), bool)

    def test_02_personas_api_structure_and_counts(self):
        """Feature 2: GET /api/personas returns 200 with exact 50 deterministic records."""
        resp = self.client.get("/api/personas")
        self.assertEqual(resp.status_code, 200, f"Personas endpoint failed: {resp.text}")
        data = resp.json()
        self.assertIn("records", data)
        records = data["records"]
        self.assertEqual(len(records), 50, f"Expected 50 records in bank, found {len(records)}")
        
        # Verify schema keys on first record
        first = records[0]
        required_keys = ["customer_id", "name", "phone", "amount_due", "days_overdue", "persona_type", "outcome_ground_truth", "response_script", "scoring_criteria"]
        for k in required_keys:
            self.assertIn(k, first, f"Missing key '{k}' in CustomerRecord schema")

    def test_03_single_turn_simulation_agree_intent(self):
        """Feature 3a: POST /api/simulate-turn detects 'agree_to_pay' and issues Razorpay link."""
        payload = {
            "customer_id": "CUST_001",
            "customer_name": "Rohit Sharma",
            "amount_due": 4500,
            "days_overdue": 12,
            "customer_utterance": "Haan bhai link bhej do abhi pay kar deta hoon",
            "turn_number": 1,
            "channel": "voice_call"
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200, f"Simulate turn failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("detected_intent"), "agree_to_pay")
        self.assertEqual(data.get("sentiment"), "Cooperative (Positive)")
        self.assertIsNotNone(data.get("payment_link"), "Payment link should be generated for agree_to_pay")
        self.assertIn("plink_", data["payment_link"]["payment_link_id"])
        self.assertIn("rzp.io", data["payment_link"]["short_url"])

    def test_04_single_turn_simulation_dispute_intent(self):
        """Feature 3b: POST /api/simulate-turn detects 'dispute_charge' and triggers stopping rule #1."""
        payload = {
            "customer_id": "CUST_002",
            "customer_name": "Priya Verma",
            "amount_due": 3200,
            "days_overdue": 18,
            "customer_utterance": "Maine ye course purchase nahi kiya, galat bill hai. Cancel karo!",
            "turn_number": 1,
            "channel": "voice_call"
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200, f"Simulate turn dispute failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("detected_intent"), "dispute_charge")
        self.assertEqual(data.get("sentiment"), "Concerned (Disputed)")
        self.assertTrue(data.get("stopping_rule_triggered"), "Dispute must trigger stopping rule")
        self.assertIsNone(data.get("payment_link"), "No payment link should be generated on dispute")

    def test_05_single_turn_simulation_reschedule_intent(self):
        """Feature 3c: POST /api/simulate-turn detects 'reschedule_request'."""
        payload = {
            "customer_id": "CUST_003",
            "customer_name": "Vikram Singh",
            "amount_due": 12000,
            "days_overdue": 24,
            "customer_utterance": "Abhi salary nahi aayi hai, next week Friday ko pakka transfer karunga",
            "turn_number": 1,
            "channel": "voice_call"
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200, f"Simulate turn reschedule failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("detected_intent"), "reschedule_request")
        self.assertEqual(data.get("state"), "RESCHEDULED")

    def test_06_single_turn_simulation_partial_payment(self):
        """Feature 3d: POST /api/simulate-turn detects 'partial_payment_offer' and bills 50%."""
        payload = {
            "customer_id": "CUST_004",
            "customer_name": "Sunil Gupta",
            "amount_due": 10000,
            "days_overdue": 15,
            "customer_utterance": "Abhi poora nahi ho payega, adha payment abhi kar deta hu 50%",
            "turn_number": 1,
            "channel": "voice_call"
        }
        resp = self.client.post("/api/simulate-turn", json=payload)
        self.assertEqual(resp.status_code, 200, f"Simulate turn partial pay failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("detected_intent"), "partial_payment_offer")
        self.assertIsNotNone(data.get("payment_link"))
        # Partial link is half amount
        self.assertEqual(data["payment_link"]["amount_inr"], 5000.0)

    def test_07_metrics_and_funnel_api(self):
        """Feature 4: GET /api/metrics returns complete summary and 4-stage funnel dictionary."""
        resp = self.client.get("/api/metrics")
        self.assertEqual(resp.status_code, 200, f"Metrics endpoint failed: {resp.text}")
        data = resp.json()
        self.assertIn("summary", data)
        self.assertIn("funnel", data)
        self.assertIn("payment_ledger", data)
        
        summary = data["summary"]
        self.assertEqual(summary.get("total_accounts"), 50)
        self.assertEqual(summary.get("total_delinquent_book_inr"), 406700)
        self.assertEqual(summary.get("simulated_recovered_inr"), 221700)
        self.assertAlmostEqual(summary.get("recovery_rate_pct"), 56.0, places=1)
        
        funnel = data["funnel"]
        self.assertIn("stage_1_contacted", funnel)
        self.assertIn("stage_2_commitment", funnel)
        self.assertIn("stage_3_link_issued", funnel)
        self.assertIn("stage_4_recovered_simulated", funnel)

    def test_08_custom_persona_injection(self):
        """Feature 5: POST /api/custom-persona registers custom sandbox profile."""
        payload = {
            "name": "Arjun Nair",
            "amount_due": 8500,
            "days_overdue": 9,
            "persona_type": "willing_forgetful",
            "opening_reply": "Haan abhi link bhejo, UPI se kar deta hu"
        }
        resp = self.client.post("/api/custom-persona", json=payload)
        self.assertEqual(resp.status_code, 200, f"Custom persona injection failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("status"), "created")
        customer = data.get("customer", {})
        self.assertTrue(customer.get("id", "").startswith("CUSTOM_"))
        self.assertEqual(customer.get("name"), "Arjun Nair")
        self.assertEqual(customer.get("amount"), 8500)

    def test_09_settlement_webhook_api(self):
        """Feature 6: POST /api/webhook/payment-captured stamps UTR and returns paid event."""
        payload = {
            "payment_link_id": "plink_test_webhook_01",
            "customer_id": "CUST_001",
            "amount_inr": 4500,
            "payment_method": "upi"
        }
        resp = self.client.post("/api/webhook/payment-captured", json=payload)
        self.assertEqual(resp.status_code, 200, f"Webhook payment failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data.get("event"), "payment_link.paid")
        payload_data = data.get("payload", {})
        self.assertEqual(payload_data.get("status"), "paid")
        self.assertEqual(payload_data.get("customer_id"), "CUST_001")
        self.assertTrue(payload_data.get("utr_number", "").startswith("UTR_RZP_"))

    def test_10_batch_evaluation_api_trigger(self):
        """Feature 7: POST /api/run-batch evaluates subset and returns 4-stage funnel."""
        resp = self.client.post("/api/run-batch?limit=5")
        self.assertEqual(resp.status_code, 200, f"Run batch failed: {resp.text}")
        data = resp.json()
        self.assertIn("funnel", data)
        self.assertIn("failure_and_non_cash_breakdown", data)
        self.assertEqual(data["funnel"]["stage_1_contacted"]["count"], 5)

    def test_11_frontend_build_artifacts_and_dependencies(self):
        """Feature 8: Validates package.json dependencies and frontend dist bundle."""
        pkg_path = WORKSPACE_ROOT / "frontend" / "package.json"
        self.assertTrue(pkg_path.exists(), "frontend/package.json must exist")
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        deps = pkg.get("dependencies", {})
        self.assertIn("react", deps, "React must be a dependency")
        self.assertIn("lucide-react", deps, "lucide-react must be a dependency")
        self.assertIn("tailwindcss", deps, "tailwindcss must be a dependency")

        dist_html = WORKSPACE_ROOT / "frontend" / "dist" / "index.html"
        self.assertTrue(dist_html.exists(), "frontend/dist/index.html must exist")
        with open(dist_html, "r", encoding="utf-8") as f:
            html_content = f.read()
        self.assertIn("<!doctype html>", html_content.lower())
        self.assertIn("assets/", html_content)

    def test_12_frontend_component_modularity(self):
        """Feature 9: Verifies modular React components exist in frontend/src/components/."""
        comp_dir = WORKSPACE_ROOT / "frontend" / "src" / "components"
        self.assertTrue(comp_dir.exists(), "frontend/src/components directory must exist")
        
        required_components = [
            "Navbar",
            "TelephonyHub",
            "BatchLedger",
            "FunnelAnalytics",
            "PersonaSandbox",
            "RazorpayModal",
            "TranscriptModal",
            "YieldCalculator"
        ]
        
        existing_files = os.listdir(comp_dir)
        for comp in required_components:
            has_file = any(f.startswith(comp) and (f.endswith(".jsx") or f.endswith(".tsx")) for f in existing_files)
            self.assertTrue(has_file, f"Component {comp} (.jsx or .tsx) must exist in frontend/src/components/")

    def test_13_speech_hook_contract(self):
        """Feature 10: Verifies useSpeechToText hook exports expected interfaces and 2.2s auto-commit."""
        hook_path_ts = WORKSPACE_ROOT / "frontend" / "src" / "hooks" / "useSpeechToText.ts"
        hook_path_js = WORKSPACE_ROOT / "frontend" / "src" / "hooks" / "useSpeechToText.js"
        hook_path = hook_path_ts if hook_path_ts.exists() else hook_path_js
        self.assertTrue(hook_path.exists(), "useSpeechToText hook must exist")
        
        with open(hook_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("useSpeechToText", content)
        self.assertIn("isListening", content)
        self.assertIn("startListening", content)
        self.assertIn("stopListening", content)
        self.assertIn("2200", content, "Hook should specify silence auto-commit timer (2.2s)")

    def test_14_hardware_mic_and_tts_ducking(self):
        """Feature 11: Speech hook requests getUserMedia and cancels active SpeechSynthesis."""
        hook_path_ts = WORKSPACE_ROOT / "frontend" / "src" / "hooks" / "useSpeechToText.ts"
        hook_path_js = WORKSPACE_ROOT / "frontend" / "src" / "hooks" / "useSpeechToText.js"
        hook_path = hook_path_ts if hook_path_ts.exists() else hook_path_js
        
        with open(hook_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("getUserMedia", content, "Hook must invoke navigator.mediaDevices.getUserMedia")
        self.assertIn("speechSynthesis.cancel", content, "Hook must cancel active TTS when microphone starts")

    def test_15_sarvam_audio_client_contracts(self):
        """Feature 13: SarvamAudioClient implements speech synthesis, transcription and usage metrics."""
        audio_client = SarvamAudioClient(api_key="your_sarvam_api_key_here")
        self.assertFalse(audio_client.has_key, "Test mode should operate with sandbox fallback")
        
        # Test simulated STT
        stt_resp = audio_client.transcribe_audio("/dev/null")
        self.assertIn("transcript", stt_resp)
        self.assertTrue(stt_resp.get("simulated", False))
        
        # Test simulated TTS
        tts_resp = audio_client.synthesize_speech("Aapka payment pending hai", speaker="aditya")
        self.assertIn("speaker", tts_resp)
        self.assertEqual(tts_resp.get("speaker"), "aditya")
        
        # Test metrics
        metrics = audio_client.get_usage_metrics()
        self.assertIn("total_chars_synthesized", metrics)
        self.assertIn("estimated_cost_inr", metrics)


class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2: Boundary & Corner Cases.
    Tests extreme inputs, empty strings, missing fields, special characters, and edge conditions.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.classifier = HinglishIntentClassifier()
        cls.rzp = RazorpayRecoveryClient()

    def test_16_empty_utterance_and_silence_classification(self):
        """Boundary: Empty, whitespace-only, and placeholder strings classify as ghost_no_response."""
        silence_inputs = ["", "   ", "\t\n", "...", "silent", "[silence]", "none"]
        for inp in silence_inputs:
            result = self.classifier.classify(inp)
            self.assertEqual(
                result["intent"],
                "ghost_no_response",
                f"Input '{inp}' should be classified as ghost_no_response, got {result['intent']}"
            )
            self.assertGreaterEqual(result["confidence"], 0.90)

    def test_17_special_characters_and_meta_characters(self):
        """Boundary: XSS scripts, SQL metacharacters, emojis, and Devanagari script are handled cleanly."""
        adversarial_inputs = [
            "<script>alert('xss')</script> haan link bhej do",
            "'; DROP TABLE users; -- kar dunga pay",
            "💳💰 Payment kar diya maine UPI se check karo! 🔥",
            "हाँ भाई लिंक भेजो अभी तुरंत पे कर देता हूँ",
            "Dispute! Cancel my bill right now & verify @#%^*()!"
        ]
        for utterance in adversarial_inputs:
            resp = self.client.post(
                "/api/simulate-turn",
                json={
                    "customer_id": "CUST_TEST",
                    "customer_name": "Edge User",
                    "amount_due": 5000,
                    "days_overdue": 10,
                    "customer_utterance": utterance,
                    "turn_number": 1
                }
            )
            self.assertEqual(resp.status_code, 200, f"Failed on special input: {utterance}")
            data = resp.json()
            self.assertIn("detected_intent", data)
            self.assertIn("agent_response", data)

    def test_18_extreme_amounts_paise_conversion(self):
        """Boundary: Zero and massive amounts convert to paise accurately (amount * 100)."""
        # Zero amount
        link_zero = self.rzp.generate_payment_link("CUST_ZERO", 0, "Zero Amount", "9876543210")
        self.assertEqual(link_zero["amount_inr"], 0.0)
        
        # Massive amount (₹1 Crore = 10,000,000 INR = 1,000,000,000 paise)
        crore_paise = 10000000 * 100
        link_crore = self.rzp.generate_payment_link("CUST_CRORE", crore_paise, "Crore User", "9876543210")
        self.assertEqual(link_crore["amount_inr"], 10000000.0)
        self.assertIn("plink_", link_crore["payment_link_id"])

    def test_19_missing_and_invalid_request_bodies(self):
        """Boundary: Missing required fields in API endpoints return 422 Unprocessable Entity."""
        # Missing customer_utterance in simulate-turn (simulate_turn requires customer_utterance)
        # Note: If schema allows defaults, check empty body
        resp = self.client.post("/api/custom-persona", json={"invalid_field": 123})
        self.assertEqual(resp.status_code, 422, "Missing required fields in custom persona must return 422")
        
        # Missing payment_link_id in webhook
        resp = self.client.post("/api/webhook/payment-captured", json={"invalid": True})
        self.assertEqual(resp.status_code, 422, "Missing fields in webhook must return 422")

    def test_20_aggressive_harassment_keywords(self):
        """Boundary: Aggressive harassment / legal threat phrases classify as aggressive_pushback."""
        threat_inputs = [
            "Baar baar call mat karo police complaint kar dunga",
            "Tamiz se baat karo dimag mat khao",
            "Stop harassing me I will file a police case"
        ]
        for threat in threat_inputs:
            result = self.classifier.classify(threat)
            self.assertEqual(
                result["intent"],
                "aggressive_pushback",
                f"Expected aggressive_pushback for '{threat}', got {result['intent']}"
            )

    def test_21_unknown_link_webhook_graceful_handling(self):
        """Boundary: Webhook called for an unissued payment_link_id registers cleanly without 500 error."""
        unique_link_id = f"plink_unknown_{hashlib.md5(b'test').hexdigest()[:8]}"
        resp = self.client.post(
            "/api/webhook/payment-captured",
            json={
                "payment_link_id": unique_link_id,
                "customer_id": "CUST_UNKNOWN",
                "amount_inr": 2500,
                "payment_method": "card"
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["event"], "payment_link.paid")
        self.assertEqual(data["payload"]["payment_link_id"], unique_link_id)

    def test_22_turn_boundary_and_exhaustion(self):
        """Boundary: Simulated turn at or beyond max turns allowed sets stopping_rule_triggered."""
        engine = RecoveryNegotiationEngine()
        record = CustomerRecord(
            customer_id="CUST_BOUND",
            name="Max Turn User",
            phone="+91-9876543210",
            preferred_language_mix="hinglish",
            amount_due=3000,
            days_overdue=10,
            payment_method_on_file="upi",
            contact_history=[],
            persona_type="willing_forgetful",
            outcome_ground_truth="pays_if_link_given",
            response_script={"default": "Theek hai"},
            scoring_criteria=ScoringCriteria(
                must_generate_link=True,
                must_log_commitment=True,
                max_turns_allowed=3
            )
        )
        decision = engine.process_turn(customer=record, turn_number=3, customer_utterance="Theek hai")
        self.assertTrue(decision.stopping_rule_triggered, "Turn 3 (max_turns) must trigger stopping rule")


class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3: Cross-Feature State Machine Combinations.
    Tests end-to-end multi-step flows combining simulation, payment link, webhook settlement, and ledger.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_23_full_recovery_payment_link_to_webhook_flow(self):
        """Combination 1: Agree to pay -> Link issued -> Webhook captured -> Ledger status updated to paid."""
        # Step 1: Simulate Turn agreeing to pay
        sim_payload = {
            "customer_id": "CUST_FLOW_01",
            "customer_name": "Karan Johar",
            "amount_due": 6500,
            "days_overdue": 14,
            "customer_utterance": "Haan link bhej do main abhi payment kar deta hu",
            "turn_number": 1
        }
        sim_resp = self.client.post("/api/simulate-turn", json=sim_payload)
        self.assertEqual(sim_resp.status_code, 200)
        sim_data = sim_resp.json()
        self.assertEqual(sim_data["detected_intent"], "agree_to_pay")
        link_info = sim_data["payment_link"]
        self.assertIsNotNone(link_info)
        payment_link_id = link_info["payment_link_id"]

        # Step 2: Verify ledger has status "issued"
        metrics_resp = self.client.get("/api/metrics")
        ledger = metrics_resp.json().get("payment_ledger", {})
        self.assertIn(payment_link_id, ledger)
        self.assertEqual(ledger[payment_link_id]["status"], "issued")

        # Step 3: Webhook payment captured
        wh_payload = {
            "payment_link_id": payment_link_id,
            "customer_id": "CUST_FLOW_01",
            "amount_inr": 6500,
            "payment_method": "upi"
        }
        wh_resp = self.client.post("/api/webhook/payment-captured", json=wh_payload)
        self.assertEqual(wh_resp.status_code, 200)
        wh_data = wh_resp.json()
        self.assertEqual(wh_data["payload"]["status"], "paid")
        self.assertTrue(wh_data["payload"]["utr_number"].startswith("UTR_RZP_"))

        # Step 4: Verify ledger updated to "paid_and_captured"
        metrics_after = self.client.get("/api/metrics")
        updated_ledger = metrics_after.json().get("payment_ledger", {})
        self.assertEqual(updated_ledger[payment_link_id]["status"], "paid_and_captured")
        self.assertEqual(updated_ledger[payment_link_id]["utr_number"], wh_data["payload"]["utr_number"])

    def test_24_dispute_voiced_halts_recovery_outreach(self):
        """Combination 2: Dispute voiced -> Stopping Rule #1 triggered -> State DISPUTE_HALTED -> No link."""
        sim_payload = {
            "customer_id": "CUST_FLOW_02",
            "customer_name": "Anita Desai",
            "amount_due": 8900,
            "days_overdue": 20,
            "customer_utterance": "Ye fraud transaction hai maine ye service kabhi use nahi ki",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=sim_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_intent"], "dispute_charge")
        self.assertEqual(data["state"], "DISPUTE_HALTED")
        self.assertTrue(data["stopping_rule_triggered"])
        self.assertIsNone(data["payment_link"])

    def test_25_ghost_no_response_halts_outreach(self):
        """Combination 3: Customer silent -> Stopping Rule #2 triggered -> State GHOST_STOPPED."""
        sim_payload = {
            "customer_id": "CUST_FLOW_03",
            "customer_name": "Siddharth Roy",
            "amount_due": 4200,
            "days_overdue": 30,
            "customer_utterance": "...",
            "turn_number": 1
        }
        resp = self.client.post("/api/simulate-turn", json=sim_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_intent"], "ghost_no_response")
        self.assertEqual(data["state"], "GHOST_STOPPED")
        self.assertTrue(data["stopping_rule_triggered"])

    def test_26_custom_persona_injection_and_evaluation(self):
        """Combination 4: Custom persona injection -> immediate single-turn simulation execution."""
        custom_payload = {
            "name": "Meera Patel",
            "amount_due": 7200,
            "days_overdue": 11,
            "persona_type": "partial_pay_willing",
            "opening_reply": "Aadha abhi de sakti hu link bhej do"
        }
        inject_resp = self.client.post("/api/custom-persona", json=custom_payload)
        self.assertEqual(inject_resp.status_code, 200)
        cust_id = inject_resp.json()["customer"]["id"]

        sim_resp = self.client.post(
            "/api/simulate-turn",
            json={
                "customer_id": cust_id,
                "customer_name": "Meera Patel",
                "amount_due": 7200,
                "days_overdue": 11,
                "customer_utterance": "Aadha abhi de sakti hu link bhej do",
                "turn_number": 1
            }
        )
        self.assertEqual(sim_resp.status_code, 200)
        sim_data = sim_resp.json()
        self.assertIn(sim_data["detected_intent"], ["partial_payment_offer", "agree_to_pay"])
        self.assertIsNotNone(sim_data["payment_link"])


class TestTier4RealWorldWorkloadTesting(unittest.TestCase):
    """
    Tier 4: Real-World Workload Testing & Ground-Truth Forensics.
    Executes full 50-record batch, validates ₹2,21,700 benchmark, and verifies cryptographic SHA256 audit logs.
    """

    @classmethod
    def setUpClass(cls):
        cls.bank_path = WORKSPACE_ROOT / "data" / "persona_bank" / "personas.json"
        with open(cls.bank_path, "r", encoding="utf-8") as f:
            cls.raw_bank = json.load(f)
        cls.bank = PersonaBank.model_validate(cls.raw_bank)

    def test_27_persona_bank_pydantic_schema_and_distribution(self):
        """Workload 1: Validates PersonaBank schema and exact persona type distribution across 50 records."""
        self.assertEqual(self.bank.total_records, 50)
        self.assertEqual(len(self.bank.records), 50)
        
        expected_distribution = {
            "willing_forgetful": 15,
            "disputes_charge": 10,
            "genuinely_cant_pay": 10,
            "ghosts_entirely": 8,
            "aggressive": 4,
            "partial_pay_willing": 3
        }
        self.assertEqual(self.bank.distribution, expected_distribution)

        # Confirm 50 unique customer IDs
        ids = [r.customer_id for r in self.bank.records]
        self.assertEqual(len(set(ids)), 50, "All 50 customer IDs must be distinct")

        # Confirm total delinquent book equals ₹406,700
        total_book = sum(r.amount_due for r in self.bank.records)
        self.assertEqual(total_book, 406700, f"Expected total portfolio book ₹406,700, got ₹{total_book}")

    def test_28_full_50_record_batch_evaluation_benchmark(self):
        """Workload 2: Full 50-record deterministic batch evaluation matches exact ₹2,21,700 benchmark."""
        metrics = run_batch_evaluation(batch_limit=50, verbose=False)
        funnel = metrics["funnel"]
        breakdown = metrics["failure_and_non_cash_breakdown"]

        # Stage 1: Contacted (50 records, ₹406,700, 100%)
        stage_1 = funnel["stage_1_contacted"]
        self.assertEqual(stage_1["count"], 50)
        self.assertEqual(stage_1["amount_inr"], 406700)
        self.assertEqual(stage_1["conversion_pct"], 100.0)

        # Stage 2: Commitment Obtained (28 records, ₹258,700, 56.0%)
        stage_2 = funnel["stage_2_commitment_obtained"]
        self.assertEqual(stage_2["count"], 28)
        self.assertEqual(stage_2["amount_inr"], 258700)
        self.assertEqual(stage_2["conversion_pct"], 56.0)

        # Stage 3: Action Issued (18 links, ₹135,000, 36.0%)
        stage_3 = funnel["stage_3_action_issued"]
        self.assertEqual(stage_3["count"], 18)
        self.assertEqual(stage_3["amount_inr"], 135000)
        self.assertEqual(stage_3["conversion_pct"], 36.0)

        # Stage 4: Recovered Simulated (28 records, ₹221,700, 56.0%, 54.5% capital conversion)
        stage_4 = funnel["stage_4_recovered_simulated"]
        self.assertEqual(stage_4["count"], 28, "Exact 28 accounts recovered")
        self.assertEqual(stage_4["amount_inr"], 221700, "Exact ₹2,21,700 capital recovered benchmark")
        self.assertEqual(stage_4["conversion_pct"], 56.0)
        self.assertEqual(stage_4["capital_conversion_pct"], 54.5)

        # Non-cash and Policy Audits
        self.assertEqual(breakdown["disputes_logged_cleanly"], 14, "14 disputes must be flagged & halted (Rule #1)")
        self.assertEqual(breakdown["ghosts_stopped_per_rule"], 8, "8 ghosts must be stopped per Rule #2")
        self.assertEqual(breakdown["promises_to_pay_rescheduled"], 10, "10 promises to pay rescheduled")
        self.assertEqual(breakdown["false_positive_hallucinations"], 0, "Zero hallucinations vs ground truth")

    def test_29_sha256_audit_trail_cryptographic_integrity(self):
        """Workload 3: Verifies SHA256 audit trail hashes for all evaluated sessions."""
        audit_logger = AuditLogger()
        engine = RecoveryNegotiationEngine()
        
        for record in self.bank.records:
            result = engine.run_full_session(record)
            entry = audit_logger.log_session(result)
            
            # Recompute canonical SHA256 hash
            raw_copy = {k: v for k, v in entry.items() if k != "audit_hash"}
            expected_hash = hashlib.sha256(json.dumps(raw_copy, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            self.assertEqual(
                entry["audit_hash"],
                expected_hash,
                f"Audit hash mismatch for customer {record.customer_id}"
            )

        audit_path = audit_logger.flush()
        self.assertTrue(os.path.exists(audit_path), f"Audit trail file missing at {audit_path}")
        with open(audit_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["total_records_evaluated"], 50)
        self.assertEqual(len(data["audit_entries"]), 50)

    def test_30_html_recovery_report_generation(self):
        """Workload 4: Verifies interactive HTML recovery report generated with valid structure."""
        report_path = WORKSPACE_ROOT / "eval" / "reports" / "recovery_report_latest.html"
        self.assertTrue(report_path.exists(), "eval/reports/recovery_report_latest.html must exist")
        self.assertGreater(report_path.stat().st_size, 1000, "HTML report should be non-trivial size")

        with open(report_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Razorpay", html)
        self.assertIn("221,700", html)
        self.assertIn("Revenue Recovery", html)


if __name__ == "__main__":
    unittest.main()
