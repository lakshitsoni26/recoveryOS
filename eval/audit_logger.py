"""
Structured Audit Trail Logger.
Records every conversational turn, reasoning step, payment action, and compliance decision.
"""
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List


class AuditLogger:
    def __init__(self, output_dir: str = "eval/reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.run_id = f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.entries: List[Dict[str, Any]] = []

    def log_session(self, session_result: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": session_result["customer_id"],
            "name": session_result["name"],
            "persona_type": session_result["persona_type"],
            "amount_due": session_result["amount_due"],
            "ground_truth": session_result["outcome_ground_truth"],
            "turns_taken": session_result["turns_taken"],
            "commitment_obtained": session_result["commitment_obtained"],
            "link_generated": session_result["link_generated"],
            "dispute_logged": session_result["dispute_logged"],
            "reschedule_date": session_result["reschedule_date"],
            "final_status": session_result["final_status"],
            "transcript": session_result["transcript_history"]
        }
        
        # Calculate cryptographic hash for audit integrity & reproducibility
        entry_hash = hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        entry["audit_hash"] = entry_hash
        self.entries.append(entry)
        return entry

    def flush(self) -> str:
        filepath = os.path.join(self.output_dir, f"audit_trail_{self.run_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": self.run_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_records_evaluated": len(self.entries),
                "audit_entries": self.entries
            }, f, indent=2)
        return filepath
