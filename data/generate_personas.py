"""
Deterministic Persona Bank Generator (v3.0.0)
Generates 50 production-grade synthetic records with fixed multi-turn response trees,
linguistic code-switching metadata, and strict outcome ground truths.
"""
import json
from datetime import datetime
from typing import List, Dict
from data.persona_bank.schemas import CustomerRecord, PersonaBank, ScoringCriteria


FIRST_NAMES = [
    "Rohit", "Priya", "Amit", "Sunita", "Vikram", "Neha", "Rahul", "Ananya", "Rajesh", "Pooja",
    "Deepak", "Sneha", "Karan", "Kavita", "Sanjay", "Ritu", "Manish", "Divya", "Alok", "Shweta",
    "Gaurav", "Meera", "Arjun", "Tanvi", "Suresh", "Ishita", "Nitin", "Bhavna", "Harish", "Preeti",
    "Vishal", "Swati", "Ashok", "Simran", "Manoj", "Aarti", "Chetan", "Jyoti", "Dinesh", "Rashmi",
    "Tarun", "Komal", "Vikas", "Monika", "Sachin", "Payal", "Pradeep", "Ruchi", "Hemant", "Nisha"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Gupta", "Iyer", "Nair", "Mehta", "Singh", "Joshi",
    "Malhotra", "Kapoor", "Chauhan", "Bhatia", "Bansal", "Saxena", "Deshmukh", "Chopra", "Kulkarni", "Sen"
]

PERSONA_DISTRIBUTION = [
    ("willing_forgetful", 15),
    ("disputes_charge", 10),
    ("genuinely_cant_pay", 10),
    ("ghosts_entirely", 8),
    ("aggressive", 4),
    ("partial_pay_willing", 3)
]

RESPONSE_TREES = {
    "willing_forgetful": {
        "turn_1_initial": "Haan bhai, actually busy tha toh dhyan nahi raha. Mujhe payment link bhej do abhi kar deta hoon.",
        "turn_2_link_sent": "Link mil gaya phone pe. Bas 2 minute ruko, UPI se clear kar raha hoon.",
        "turn_3_followup": "Ho gaya payment successfully! Thank you reminder ke liye.",
        "default": "Haan link check kar liya maine, abhi pay kar diya hai."
    },
    "disputes_charge": {
        "turn_1_initial": "Arre par maine yeh service cancel kar di thi pichle hafte! Yeh charge galat aaya hai.",
        "turn_2_dispute_ack": "Haan please dispute ticket raise karo. Main tab tak pay nahi karunga jab tak rectify nahi hota.",
        "turn_3_followup": "Theek hai, confirmation message bhej do dispute reference number ke saath.",
        "default": "Main dispute team se baat karne ke baad hi check karunga."
    },
    "genuinely_cant_pay": {
        "turn_1_initial": "Sir sach bataun toh abhi salary delay ho gayi hai company mein. Is week thoda tight chal raha hai.",
        "turn_2_reschedule": "Agar aap coming Friday tak ka time de sakte hain toh main pakka full amount pay kar dunga.",
        "turn_3_followup": "Friday ko 11 AM tak link bhej dena, main tab payment transfer kar dunga.",
        "default": "Friday tak wait kijiye please, main commit kar raha hoon."
    },
    "ghosts_entirely": {
        "turn_1_initial": "...",
        "turn_2_link_sent": "...",
        "turn_3_followup": "...",
        "default": "..."
    },
    "aggressive": {
        "turn_1_initial": "Kyu baar baar call kar rahe ho din mein? Main fraud nahi hoon, time milte hi dekh lunga!",
        "turn_2_deescalate": "Aap respectful baat kar rahe hain toh theek hai. Mujhe WhatsApp pe payment link send kar do, sham ko dekhta hoon.",
        "turn_3_followup": "Theek hai shaam tak ho jayega.",
        "default": "Aap message kar dijiye bas."
    },
    "partial_pay_willing": {
        "turn_1_initial": "Total amount ₹{amount} bohot jyada hai ek baar mein. Kya main abhi half pay kar sakta hoon?",
        "turn_2_partial_link": "Haan ₹{half_amount} ka link bhejo abhi, baki remaining next month 5th ko kar dunga.",
        "turn_3_followup": "Half payment kar di maine, balance ka receipt bhej dena.",
        "default": "Main partial clear kar raha hoon."
    }
}

GROUND_TRUTH_MAP = {
    "willing_forgetful": "pays_if_link_given",
    "disputes_charge": "dispute_logged_success",
    "genuinely_cant_pay": "reschedule_obtained",
    "ghosts_entirely": "ghost_logged_correct",
    "aggressive": "de_escalated",
    "partial_pay_willing": "partial_commitment"
}

SCORING_CRITERIA_MAP = {
    "willing_forgetful": ScoringCriteria(must_generate_link=True, must_log_commitment=True, must_log_dispute=False, must_escalate=False, max_turns_allowed=3),
    "disputes_charge": ScoringCriteria(must_generate_link=False, must_log_commitment=False, must_log_dispute=True, must_escalate=False, max_turns_allowed=2),
    "genuinely_cant_pay": ScoringCriteria(must_generate_link=False, must_log_commitment=True, must_log_dispute=False, must_escalate=False, max_turns_allowed=3),
    "ghosts_entirely": ScoringCriteria(must_generate_link=False, must_log_commitment=False, must_log_dispute=False, must_escalate=False, max_turns_allowed=1),
    "aggressive": ScoringCriteria(must_generate_link=True, must_log_commitment=True, must_log_dispute=False, must_escalate=False, max_turns_allowed=3),
    "partial_pay_willing": ScoringCriteria(must_generate_link=True, must_log_commitment=True, must_log_dispute=False, must_escalate=False, max_turns_allowed=3)
}


def generate_all_personas() -> PersonaBank:
    records: List[CustomerRecord] = []
    idx = 0
    
    amounts_by_persona = {
        "willing_forgetful": [1200, 2500, 4500, 3200, 1800, 5000, 7500, 2100, 3900, 6200, 1500, 8900, 4200, 3100, 5400],
        "disputes_charge": [8500, 3400, 12000, 4500, 6700, 2900, 9500, 5100, 7800, 4300],
        "genuinely_cant_pay": [15000, 6800, 22000, 9500, 14000, 5500, 18500, 11000, 13500, 7900],
        "ghosts_entirely": [2500, 4900, 3100, 8200, 1500, 6400, 9100, 3800],
        "aggressive": [11500, 8900, 16000, 7400],
        "partial_pay_willing": [24000, 18000, 32000]
    }
    
    days_overdue_by_persona = {
        "willing_forgetful": [3, 5, 7, 4, 8, 6, 9, 2, 5, 11, 4, 10, 6, 7, 5],
        "disputes_charge": [12, 18, 25, 14, 20, 16, 22, 19, 28, 15],
        "genuinely_cant_pay": [19, 24, 35, 21, 29, 17, 33, 26, 31, 22],
        "ghosts_entirely": [15, 30, 45, 20, 38, 25, 42, 28],
        "aggressive": [14, 21, 28, 17],
        "partial_pay_willing": [22, 27, 34]
    }
    
    payment_methods = ["upi", "credit_card", "debit_card", "netbanking"]
    lang_mixes = ["hinglish", "hindi_dominant", "english_dominant"]

    for persona_type, count in PERSONA_DISTRIBUTION:
        for i in range(count):
            idx += 1
            cust_id = f"CUST_{idx:03d}"
            name = f"{FIRST_NAMES[(idx-1) % len(FIRST_NAMES)]} {LAST_NAMES[(idx*3) % len(LAST_NAMES)]}"
            phone = f"+91-98{idx:02d}7{idx:02d}10"
            amount = amounts_by_persona[persona_type][i]
            days = days_overdue_by_persona[persona_type][i]
            pm = payment_methods[idx % len(payment_methods)]
            lang = lang_mixes[idx % len(lang_mixes)]
            
            # Format custom response scripts with dynamic amounts if applicable
            raw_tree = RESPONSE_TREES[persona_type]
            tree = {}
            for k, v in raw_tree.items():
                tree[k] = v.replace("{amount}", str(amount)).replace("{half_amount}", str(amount // 2))

            record = CustomerRecord(
                customer_id=cust_id,
                name=name,
                phone=phone,
                preferred_language_mix=lang,
                amount_due=amount,
                days_overdue=days,
                payment_method_on_file=pm,
                contact_history=[],
                persona_type=persona_type,
                outcome_ground_truth=GROUND_TRUTH_MAP[persona_type],
                response_script=tree,
                scoring_criteria=SCORING_CRITERIA_MAP[persona_type],
                metadata={
                    "risk_tier": "HIGH" if days > 20 else ("MEDIUM" if days > 10 else "LOW"),
                    "category": persona_type
                }
            )
            records.append(record)

    bank = PersonaBank(
        version="3.0.0",
        created_at=datetime.utcnow().isoformat() + "Z",
        description="Deterministic 50-record persona bank for Razorpay AI Revenue Recovery Hackathon (Track 3)",
        total_records=len(records),
        distribution={p: c for p, c in PERSONA_DISTRIBUTION},
        records=records
    )
    return bank


if __name__ == "__main__":
    bank = generate_all_personas()
    output_path = "data/persona_bank/personas.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bank.model_dump_json(indent=2))
    print(f"✅ Generated {bank.total_records} deterministic personas at {output_path}")
    print(f"📊 Distribution: {bank.distribution}")
    total_revenue = sum(r.amount_due for r in bank.records)
    print(f"💰 Total At-Risk Revenue in Batch: ₹{total_revenue:,}")
