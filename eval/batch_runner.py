"""
Master Batch Evaluation Orchestrator (Path A).
Runs sequential evaluation across 50 records, tracks live state in rich terminal UI,
calculates 4-stage funnel vs labeled ground-truth, and outputs HTML & JSON reports.
"""
import sys
import json
import argparse
from pathlib import Path
from typing import List

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.persona_bank.schemas import PersonaBank, CustomerRecord
from integrations.razorpay_client import RazorpayRecoveryClient
from agent.intent_classifier import HinglishIntentClassifier
from agent.llm_client import RecoveryLLMClient
from agent.negotiation_engine import RecoveryNegotiationEngine
from eval.audit_logger import AuditLogger
from eval.funnel_scorer import FunnelScorer
from eval.dashboard import print_banner, render_evaluation_summary
from eval.report_generator import generate_html_report


def run_batch_evaluation(batch_limit: int = 50, verbose: bool = False):
    print_banner()
    
    bank_path = Path(__file__).resolve().parent.parent / "data" / "persona_bank" / "personas.json"
    if not bank_path.exists():
        bank_path = Path("data/persona_bank/personas.json")
    if not bank_path.exists():
        raise FileNotFoundError(f"Persona bank file missing at {bank_path}. Run generate_personas.py first.")

    with open(bank_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bank = PersonaBank.model_validate(data)
    
    records_to_run = bank.records[:batch_limit]
    print(f"🚀 Initializing Batch Run: {len(records_to_run)} Records Loaded...")
    
    # Initialize Engine Components
    rzp_client = RazorpayRecoveryClient()
    llm_client = RecoveryLLMClient()
    classifier = HinglishIntentClassifier()
    engine = RecoveryNegotiationEngine(
        razorpay_client=rzp_client,
        llm_client=llm_client,
        intent_classifier=classifier
    )
    audit_logger = AuditLogger()
    scorer = FunnelScorer()

    session_results = []
    
    for i, record in enumerate(records_to_run, 1):
        result = engine.run_full_session(record)
        session_results.append(result)
        audit_logger.log_session(result)
        
        status_icon = "💰" if result["link_generated"] else ("🛡️" if result["dispute_logged"] else "👻")
        if verbose:
            print(f"[{i:02d}/{len(records_to_run)}] {record.customer_id} ({record.name}) -> {status_icon} {result['final_status']}")

    # Flush audit trail
    audit_file = audit_logger.flush()
    print(f"\n[Audit Trail] Saved full per-turn JSON audit trail to {audit_file}")

    # Compute 4-Stage Funnel
    total_at_risk = sum(r.amount_due for r in records_to_run)
    evaluation_metrics = scorer.evaluate_batch(session_results)
    
    # Render Terminal Summary Table
    render_evaluation_summary(evaluation_metrics, total_at_risk)

    # Generate HTML Report
    html_report_path = generate_html_report(evaluation_metrics, audit_logger.entries)
    print(f"📄 [HTML Report] Interactive Report generated at {html_report_path}")
    return evaluation_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Razorpay Recovery Batch Evaluation")
    parser.add_argument("--limit", type=int, default=50, help="Number of records to evaluate (e.g. 5 or 50)")
    parser.add_argument("--verbose", action="store_true", help="Print real-time per-record progress")
    args = parser.parse_args()
    
    run_batch_evaluation(batch_limit=args.limit, verbose=args.verbose)
