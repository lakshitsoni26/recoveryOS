"""
Validation and Test Suite for the Persona Bank.
Runs automated checks to assert determinism, schema adherence, ground-truth validity,
and statistical distribution requirements.
"""
import unittest
import json
from pathlib import Path
from data.persona_bank.schemas import PersonaBank, CustomerRecord


class TestPersonaBank(unittest.TestCase):
    def setUp(self):
        self.bank_path = Path("data/persona_bank/personas.json")
        self.assertTrue(self.bank_path.exists(), "personas.json must exist")
        with open(self.bank_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.bank = PersonaBank.model_validate(self.data)

    def test_total_count(self):
        self.assertEqual(self.bank.total_records, 50, "Persona bank must contain exactly 50 records")
        self.assertEqual(len(self.bank.records), 50)

    def test_unique_customer_ids(self):
        ids = [r.customer_id for r in self.bank.records]
        self.assertEqual(len(ids), len(set(ids)), "Customer IDs must be strictly unique")

    def test_distribution(self):
        dist = self.bank.distribution
        self.assertEqual(dist.get("willing_forgetful"), 15)
        self.assertEqual(dist.get("disputes_charge"), 10)
        self.assertEqual(dist.get("genuinely_cant_pay"), 10)
        self.assertEqual(dist.get("ghosts_entirely"), 8)
        self.assertEqual(dist.get("aggressive"), 4)
        self.assertEqual(dist.get("partial_pay_willing"), 3)

    def test_ground_truth_and_response_trees(self):
        for record in self.bank.records:
            self.assertGreater(record.amount_due, 0, f"Amount due must be positive for {record.customer_id}")
            self.assertGreater(record.days_overdue, 0, f"Days overdue must be positive for {record.customer_id}")
            self.assertIn("turn_1_initial", record.response_script, f"Turn 1 script missing for {record.customer_id}")
            self.assertIn(record.preferred_language_mix, ["hinglish", "hindi_dominant", "english_dominant"])
            self.assertIsNotNone(record.outcome_ground_truth)
            self.assertIsNotNone(record.scoring_criteria)

    def test_total_at_risk_capital(self):
        total_rev = sum(r.amount_due for r in self.bank.records)
        self.assertGreater(total_rev, 300000, "Total simulated at-risk revenue should exceed ₹300k")
        print(f"\n[Validation] Total Portfolio At-Risk Revenue: ₹{total_rev:,}")


if __name__ == "__main__":
    unittest.main()
