"""
Razorpay Payment Gateway Integration Layer.
Supports real Razorpay Test-Mode API with seamless deterministic Mock fallback.
"""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class RazorpayRecoveryClient:
    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")
        self.is_live_test_mode = bool(self.key_id.startswith("rzp_test_") and len(self.key_secret) > 4)
        
        self.client = None
        if self.is_live_test_mode:
            try:
                import razorpay
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as e:
                print(f"[RazorpayClient] Warning: Failed to init Razorpay SDK: {e}. Falling back to sandbox simulator.")
                self.is_live_test_mode = False

        self._local_link_registry: Dict[str, Dict[str, Any]] = {}

    def generate_payment_link(
        self,
        customer_id: str,
        amount_paise: int,
        customer_name: str,
        customer_phone: str,
        description: Optional[str] = None,
        expire_hours: int = 48,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates an actionable Razorpay payment link.
        Amount must be in paise (e.g., ₹500 = 50000 paise).
        """
        now = datetime.now(timezone.utc)
        expire_by = int((now + timedelta(hours=expire_hours)).timestamp())
        link_desc = description or f"Recovery settlement for account {customer_id}"
        
        payload_notes = {
            "source": "hinglish_revenue_recovery_agent",
            "track": "track_3_ai_recovery",
            "customer_id": customer_id,
            "created_at_utc": now.isoformat(),
            **(notes or {})
        }

        if self.is_live_test_mode and self.client:
            try:
                payload = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "accept_partial": False,
                    "description": link_desc,
                    "customer": {
                        "name": customer_name,
                        "contact": customer_phone
                    },
                    "notify": {"sms": False, "email": False},
                    "reminder_enable": False,
                    "notes": payload_notes,
                    "expire_by": expire_by
                }
                resp = self.client.payment_link.create(payload)
                result = {
                    "payment_link_id": resp.get("id"),
                    "short_url": resp.get("short_url"),
                    "amount_inr": amount_paise / 100.0,
                    "status": resp.get("status", "created"),
                    "expires_at": expire_by,
                    "is_live_gateway": True
                }
                self._local_link_registry[resp.get("id")] = result
                return result
            except Exception as err:
                print(f"[RazorpayClient] API call failed: {err}. Emulating test-mode link response.")

        # Sandbox / Deterministic Fallback Mode
        link_id = f"plink_test_{uuid.uuid4().hex[:10]}"
        result = {
            "payment_link_id": link_id,
            "short_url": "https://rzp.io/rzp/gTXQ9yH",
            "amount_inr": amount_paise / 100.0,
            "status": "created",
            "expires_at": expire_by,
            "is_live_gateway": False,
            "simulated": True,
            "notes": payload_notes
        }
        self._local_link_registry[link_id] = result
        return result

    def verify_link_status(self, payment_link_id: str) -> str:
        """
        Fetches latest payment status: created | paid | expired | cancelled
        """
        if self.is_live_test_mode and self.client:
            try:
                resp = self.client.payment_link.fetch(payment_link_id)
                return resp.get("status", "unknown")
            except Exception:
                pass
        
        entry = self._local_link_registry.get(payment_link_id)
        if entry:
            return entry.get("status", "created")
        return "created"
