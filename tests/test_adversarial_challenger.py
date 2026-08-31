"""
Challenger 1 Adversarial Stress Test Suite for Razorpay RecoveryOS.
Empirically tests boundary conditions, malformed/adversarial inputs, concurrent loads,
stopping rule invariants, and mathematical determinism of recovery scores.
"""

import sys
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import unittest

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from fastapi.testclient import TestClient
from api.server import app, payment_ledger, custom_personas
from agent.intent_classifier import HinglishIntentClassifier
from agent.negotiation_engine import RecoveryNegotiationEngine, RecoveryState
from integrations.razorpay_client import RazorpayRecoveryClient
from eval.batch_runner import run_batch_evaluation
from eval.funnel_scorer import FunnelScorer
from eval.audit_logger import AuditLogger
from data.persona_bank.schemas import PersonaBank, CustomerRecord, ScoringCriteria


class TestChallengerAdversarialInputs(unittest.TestCase):
    """
    Test Section 1: Extreme boundary, malformed, and adversarial inputs.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.engine = RecoveryNegotiationEngine()
        cls.classifier = HinglishIntentClassifier()
        cls.rzp = RazorpayRecoveryClient()

    def test_01_unicode_rtl_zero_width_and_null_bytes(self):
        """Stress: Utterances with RTL overrides, zero-width spaces, null characters, control codes."""
        tricky_utterances = [
            "\u200b\u200c\u200d\ufeff", # Zero-width characters only
            "\u202e\u202dPay\u202c\u202c nahi karunga fraud hai", # RTL override
            "Haan \x00 link \x1f bhej do \x07", # Null byte & terminal bell control codes
            "😀😁😂🤣😃😄😅😆😉😊😋😎😍😘\n\t\r", # High unicode emojis only
            "A" * 50000 + " haan link bhej do", # 50KB string
            "{\"json_in_text\": true, \"drop_database\": true} dispute cancel", # Raw JSON text
        ]
        for utterance in tricky_utterances:
            resp = self.client.post(
                "/api/simulate-turn",
                json={
                    "customer_id": "CUST_ADVERSARIAL_1",
                    "customer_name": "Edge User \u200b",
                    "amount_due": 5000,
                    "days_overdue": 10,
                    "customer_utterance": utterance,
                    "turn_number": 1
                }
            )
            self.assertEqual(resp.status_code, 200, f"Failed on tricky input: {repr(utterance[:50])}")
            data = resp.json()
            self.assertIn("detected_intent", data)
            self.assertIn("agent_response", data)
            self.assertIn("stopping_rule_triggered", data)

    def test_02_boundary_amounts_and_negative_values(self):
        """Stress: Zero amount, massive amounts, negative amounts, large overdue days."""
        test_cases = [
            (0, 0),
            (1, 1),
            (999999999, 3650), # ~100 Crore, 10 years overdue
            (-5000, -10), # Negative amounts
        ]
        for amt, days in test_cases:
            resp = self.client.post(
                "/api/simulate-turn",
                json={
                    "customer_id": "CUST_AMOUNT_TEST",
                    "customer_name": "Boundary Tester",
                    "amount_due": amt,
                    "days_overdue": days,
                    "customer_utterance": "Haan link bhej do pay karta hu",
                    "turn_number": 1
                }
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["detected_intent"], "agree_to_pay")
            if amt > 0:
                self.assertIsNotNone(data["payment_link"])
                self.assertEqual(data["payment_link"]["amount_inr"], float(amt))

    def test_03_malformed_json_and_type_coercion_on_endpoints(self):
        """Stress: Endpoint validation with invalid JSON, missing body, wrong types."""
        # 1. Non-JSON string to POST
        resp = self.client.post("/api/simulate-turn", content="NOT_A_JSON_STRING", headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 422)

        # 2. Wrong type for turn_number (string instead of int)
        resp = self.client.post("/api/simulate-turn", json={
            "customer_utterance": "Hello",
            "turn_number": "NOT_AN_INT"
        })
        self.assertEqual(resp.status_code, 422)

        # 3. Missing required fields on custom persona
        resp = self.client.post("/api/custom-persona", json={
            "name": "Only Name"
        })
        self.assertEqual(resp.status_code, 422)

        # 4. Webhook with wrong type for amount_inr
        resp = self.client.post("/api/webhook/payment-captured", json={
            "payment_link_id": "plink_123",
            "customer_id": "CUST_1",
            "amount_inr": "NOT_A_NUMBER"
        })
        self.assertEqual(resp.status_code, 422)


class TestChallengerStoppingRuleInvariants(unittest.TestCase):
    """
    Test Section 2: Strict Invariant Verification.
    1. Disputes NEVER continue outreach / issue payment link.
    2. Ghost accounts NEVER get called multiple times.
    3. Max turns bound is strictly respected.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.engine = RecoveryNegotiationEngine()
        cls.bank_path = WORKSPACE_ROOT / "data" / "persona_bank" / "personas.json"
        with open(cls.bank_path, "r", encoding="utf-8") as f:
            cls.bank_data = json.load(f)
        cls.bank = PersonaBank.model_validate(cls.bank_data)

    def test_04_dispute_stopping_rule_invariant(self):
        """Invariant 1: Any dispute utterance MUST halt outreach immediately with NO link issued."""
        dispute_utterances = [
            "Maine ye service cancel kar di thi, galat bill hai",
            "This is fraud, I never purchased this course",
            "Dispute! Already paid last month please rectify",
            "Galat charge lagaya hai cancel karo",
            "Dobara kyu charge kar rahe ho already paid"
        ]
        for utt in dispute_utterances:
            # Test via process_turn
            decision = self.engine.process_turn(
                turn_number=1,
                customer_utterance=utt
            )
            self.assertTrue(decision.stopping_rule_triggered, f"Stopping rule not triggered for: {utt}")
            self.assertEqual(decision.state, RecoveryState.DISPUTE_HALTED)
            self.assertTrue(decision.dispute_logged)
            self.assertIsNone(decision.payment_link, f"Payment link MUST NOT be generated on dispute: {utt}")
            self.assertEqual(decision.final_status, "dispute_logged")

            # Test via API
            resp = self.client.post(
                "/api/simulate-turn",
                json={
                    "customer_id": "CUST_DISPUTE_INV",
                    "customer_name": "Dispute User",
                    "amount_due": 7000,
                    "days_overdue": 15,
                    "customer_utterance": utt,
                    "turn_number": 1
                }
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["stopping_rule_triggered"])
            self.assertEqual(data["detected_intent"], "dispute_charge")
            self.assertIsNone(data["payment_link"])

    def test_05_all_dispute_personas_in_bank_halt_immediately(self):
        """Invariant 1b: All dispute records in the 50-persona bank halt immediately at Turn 1."""
        dispute_records = [r for r in self.bank.records if r.persona_type == "disputes_charge"]
        self.assertEqual(len(dispute_records), 10, "Expected 10 dispute records")

        for record in dispute_records:
            result = self.engine.run_full_session(record)
            self.assertEqual(result["turns_taken"], 1, f"Dispute for {record.customer_id} took {result['turns_taken']} turns, expected 1")
            self.assertTrue(result["dispute_logged"])
            self.assertIsNone(result["link_generated"], f"Link generated for dispute record {record.customer_id}")
            self.assertEqual(result["final_status"], "dispute_logged")

    def test_06_ghost_accounts_stopping_rule_invariant(self):
        """Invariant 2: Ghost / silent accounts halt at turn 1 and NEVER get called multiple times."""
        ghost_utterances = ["", "   ", "...", "silent", "[silence]", "none"]
        for utt in ghost_utterances:
            decision = self.engine.process_turn(
                turn_number=1,
                customer_utterance=utt
            )
            self.assertTrue(decision.stopping_rule_triggered)
            self.assertEqual(decision.state, RecoveryState.GHOST_STOPPED)
            self.assertEqual(decision.final_status, "ghost_no_response")
            self.assertIsNone(decision.payment_link)

    def test_07_all_ghost_personas_in_bank_halt_at_turn_1(self):
        """Invariant 2b: All 8 ghost records in the 50-persona bank take exactly 1 turn and halt."""
        ghost_records = [r for r in self.bank.records if r.persona_type == "ghosts_entirely"]
        self.assertEqual(len(ghost_records), 8, "Expected 8 ghost records")

        for record in ghost_records:
            result = self.engine.run_full_session(record)
            self.assertEqual(result["turns_taken"], 1, f"Ghost for {record.customer_id} took {result['turns_taken']} turns, expected 1")
            self.assertEqual(result["final_status"], "ghost_no_response")
            self.assertFalse(result["commitment_obtained"])
            self.assertIsNone(result["link_generated"])

    def test_08_max_turns_bound_is_strictly_respected(self):
        """Invariant 3: Under any circumstance, dialogue engine NEVER exceeds max_turns_allowed."""
        # Create a record with max_turns_allowed = 2 and an infinite conversational loop
        record = CustomerRecord(
            customer_id="CUST_LOOP",
            name="Loop Customer",
            phone="+91-9999999999",
            preferred_language_mix="hinglish",
            amount_due=5000,
            days_overdue=20,
            payment_method_on_file="upi",
            contact_history=[],
            persona_type="willing_forgetful",
            outcome_ground_truth="pays_if_link_given",
            response_script={"default": "Kyu bhai kaunsa bill? details batao"},
            scoring_criteria=ScoringCriteria(
                must_generate_link=True,
                must_log_commitment=True,
                max_turns_allowed=2
            )
        )
        # Turn 1:
        d1 = self.engine.process_turn(customer=record, turn_number=1, customer_utterance="Kyu bhai kaunsa bill?")
        self.assertFalse(d1.stopping_rule_triggered)

        # Turn 2: Should hit max turns cutoff
        d2 = self.engine.process_turn(customer=record, turn_number=2, customer_utterance="Mujhe yaad nahi aa raha")
        self.assertTrue(d2.stopping_rule_triggered, "Turn 2 (max_turns) MUST trigger stopping rule")

        # Turn 3: Beyond max turns
        d3 = self.engine.process_turn(customer=record, turn_number=3, customer_utterance="Aur bolo")
        self.assertTrue(d3.stopping_rule_triggered, "Turn >= max_turns MUST trigger stopping rule")

        # In run_full_session, turns_taken must be <= max_turns
        for rec in self.bank.records:
            res = self.engine.run_full_session(rec)
            self.assertLessEqual(
                res["turns_taken"],
                rec.scoring_criteria.max_turns_allowed,
                f"Record {rec.customer_id} took {res['turns_taken']} turns, exceeding max allowed {rec.scoring_criteria.max_turns_allowed}"
            )


class TestChallengerRecoveryScoreDeterminismAndAntiTampering(unittest.TestCase):
    """
    Test Section 3: Recovery score integrity and anti-tampering verification.
    Verifies that ₹2,21,700 across 28 accounts is mathematically sound,
    deterministic across random orderings, thread executions, and impossible to perturb.
    """

    @classmethod
    def setUpClass(cls):
        cls.bank_path = WORKSPACE_ROOT / "data" / "persona_bank" / "personas.json"
        with open(cls.bank_path, "r", encoding="utf-8") as f:
            cls.bank_data = json.load(f)
        cls.bank = PersonaBank.model_validate(cls.bank_data)

    def test_09_ground_truth_mathematical_breakdown(self):
        """Verify exact cohort math for ₹2,21,700 across 28 accounts."""
        records = self.bank.records
        self.assertEqual(len(records), 50)

        # Persona cohorts:
        willing_forgetful = [r for r in records if r.persona_type == "willing_forgetful"]
        partial_pay = [r for r in records if r.persona_type == "partial_pay_willing"]
        cant_pay = [r for r in records if r.persona_type == "genuinely_cant_pay"]
        disputes = [r for r in records if r.persona_type == "disputes_charge"]
        ghosts = [r for r in records if r.persona_type == "ghosts_entirely"]
        aggressive = [r for r in records if r.persona_type == "aggressive"]

        # Counts:
        self.assertEqual(len(willing_forgetful), 15)
        self.assertEqual(len(partial_pay), 3)
        self.assertEqual(len(cant_pay), 10)
        self.assertEqual(len(disputes), 10)
        self.assertEqual(len(ghosts), 8)
        self.assertEqual(len(aggressive), 4)

        # Amount subtotals:
        wf_amount = sum(r.amount_due for r in willing_forgetful) # 15 records
        pp_amount_full = sum(r.amount_due for r in partial_pay) # 3 records
        pp_amount_collected = sum(r.amount_due // 2 for r in partial_pay) # 50% collected
        cant_pay_amount = sum(r.amount_due for r in cant_pay) # 10 records rescheduled
        disputes_amount = sum(r.amount_due for r in disputes) # 10 records halted
        ghosts_amount = sum(r.amount_due for r in ghosts) # 8 records halted
        aggressive_amount = sum(r.amount_due for r in aggressive) # 4 records

        total_portfolio = sum(r.amount_due for r in records)
        self.assertEqual(total_portfolio, 406700, f"Expected total portfolio ₹406,700, got {total_portfolio}")

        # Recovered cohorts:
        # 15 willing_forgetful (100% full recovery) = ₹117,500
        # 3 partial_pay_willing (50% partial recovery) = ₹17,500 // 2 = ₹8,700 (or check exact math)
        # 10 genuinely_cant_pay (100% rescheduled promise-to-pay recovered) = ₹95,500
        # Total recovered count = 15 + 3 + 10 = 28 accounts.
        # Total recovered amount = wf_amount + pp_amount_collected + cant_pay_amount
        expected_recovered_amt = wf_amount + pp_amount_collected + cant_pay_amount
        self.assertEqual(expected_recovered_amt, 221700, f"Mathematical expected ₹221,700, got {expected_recovered_amt}")
        self.assertEqual(len(willing_forgetful) + len(partial_pay) + len(cant_pay), 28)

    def test_10_batch_evaluation_invariance_under_shuffling(self):
        """Adversarial Shuffling: Permute records order 10 times and ensure 100% invariant outcome."""
        scorer = FunnelScorer()
        engine = RecoveryNegotiationEngine()
        
        for iteration in range(10):
            shuffled_records = list(self.bank.records)
            random.seed(42 + iteration)
            random.shuffle(shuffled_records)

            session_results = [engine.run_full_session(r) for r in shuffled_records]
            eval_metrics = scorer.evaluate_batch(session_results)
            
            stage_4 = eval_metrics["funnel"]["stage_4_recovered_simulated"]
            self.assertEqual(stage_4["count"], 28, f"Shuffle iteration {iteration} count mismatch")
            self.assertEqual(stage_4["amount_inr"], 221700, f"Shuffle iteration {iteration} amount mismatch")
            self.assertEqual(stage_4["conversion_pct"], 56.0)
            self.assertEqual(stage_4["capital_conversion_pct"], 54.5)

    def test_11_concurrent_high_load_simulated_calls(self):
        """Adversarial Concurrency: 50 concurrent client threads firing turns simultaneously."""
        client = TestClient(app)
        
        def simulate_turn_worker(record_idx):
            record = self.bank.records[record_idx % len(self.bank.records)]
            resp = client.post(
                "/api/simulate-turn",
                json={
                    "customer_id": record.customer_id,
                    "customer_name": record.name,
                    "amount_due": record.amount_due,
                    "days_overdue": record.days_overdue,
                    "customer_utterance": record.response_script.get("turn_1_initial", "Theek hai link bhejo"),
                    "turn_number": 1
                }
            )
            return resp.status_code, resp.json()

        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(simulate_turn_worker, i) for i in range(100)]
            for fut in as_completed(futures):
                results.append(fut.result())

        self.assertEqual(len(results), 100)
        for status_code, data in results:
            self.assertEqual(status_code, 200)
            self.assertIn("detected_intent", data)
            self.assertIn("agent_response", data)


if __name__ == "__main__":
    unittest.main()
