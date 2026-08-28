"""
Negotiation State Machine and Workflow Orchestrator.
Executes bounded turns, applies stopping rules, and manages Razorpay payment lifecycle.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from data.persona_bank.schemas import CustomerRecord, ScoringCriteria
from integrations.razorpay_client import RazorpayRecoveryClient
from agent.intent_classifier import HinglishIntentClassifier
from agent.llm_client import RecoveryLLMClient


class RecoveryState(str, Enum):
    INITIAL = "INITIAL"
    AWAITING_REPLY = "AWAITING_REPLY"
    LINK_ISSUED = "LINK_ISSUED"
    DISPUTE_HALTED = "DISPUTE_HALTED"
    GHOST_STOPPED = "GHOST_STOPPED"
    RESCHEDULED = "RESCHEDULED"
    DE_ESCALATED = "DE_ESCALATED"
    MAX_TURNS_REACHED = "MAX_TURNS_REACHED"
    UNRESOLVED = "UNRESOLVED"


class PaymentLinkInfo(BaseModel):
    payment_link_id: str
    short_url: str
    amount_inr: float
    status: str = "created"
    expires_at: Optional[int] = None
    is_live_gateway: bool = False
    simulated: bool = False
    notes: Optional[Dict[str, Any]] = None


class TurnDecision(BaseModel):
    turn: int
    customer_utterance: str
    detected_intent: str
    intent_confidence: float
    sentiment: str
    agent_response: str
    reasoning: str
    stopping_rule_triggered: bool
    state: RecoveryState
    payment_link: Optional[PaymentLinkInfo] = None
    dispute_logged: bool = False
    reschedule_date: Optional[str] = None
    escalated_to_human: bool = False
    final_status: str = "active"


class RecoveryNegotiationEngine:
    def __init__(
        self,
        razorpay_client: Optional[RazorpayRecoveryClient] = None,
        llm_client: Optional[RecoveryLLMClient] = None,
        intent_classifier: Optional[HinglishIntentClassifier] = None
    ):
        self.razorpay = razorpay_client or RazorpayRecoveryClient()
        self.llm = llm_client or RecoveryLLMClient()
        self.classifier = intent_classifier or HinglishIntentClassifier()

    def process_turn(
        self,
        customer: Optional[CustomerRecord] = None,
        turn_number: int = 1,
        customer_utterance: str = "",
        channel: Optional[str] = "voice_call",
        record: Optional[CustomerRecord] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> TurnDecision:
        """
        Evaluates a single customer turn against the recovery state machine and returns
        empathetic Hinglish dialogue, stopping rule decisions, and active Razorpay link.
        """
        cust = customer or record
        if cust is None:
            cust = CustomerRecord(
                customer_id="CUST_001",
                name="Rohit Sharma",
                phone="+91-9876543210",
                preferred_language_mix="hinglish",
                amount_due=4500,
                days_overdue=12,
                payment_method_on_file="upi",
                contact_history=[],
                persona_type="willing_forgetful",
                outcome_ground_truth="pays_if_link_given",
                response_script={str(turn_number): customer_utterance, "turn_1_initial": customer_utterance, "default": customer_utterance},
                scoring_criteria=ScoringCriteria(
                    must_generate_link=True,
                    must_log_commitment=True,
                    must_log_dispute=False,
                    must_escalate=False,
                    max_turns_allowed=3
                )
            )

        max_turns = cust.scoring_criteria.max_turns_allowed if cust.scoring_criteria else 3

        # Intent Classification
        classification = self.classifier.classify(customer_utterance)
        intent = classification.get("intent", "neutral_query")
        confidence = float(classification.get("confidence", 0.60))

        # Sentiment Analysis
        if intent in ["agree_to_pay", "partial_payment_offer"]:
            sentiment = "Cooperative (Positive)"
        elif intent == "dispute_charge":
            sentiment = "Concerned (Disputed)"
        elif intent == "aggressive_pushback":
            sentiment = "Agitated (Negative)"
        elif intent == "ghost_no_response":
            sentiment = "Unresponsive (Silent)"
        elif intent == "reschedule_request":
            sentiment = "Negotiating (Neutral)"
        else:
            sentiment = "Neutral"

        # Policy & Stopping Rules Evaluation
        stopping_rule_triggered = False
        state = RecoveryState.AWAITING_REPLY
        payment_link_info: Optional[PaymentLinkInfo] = None
        dispute_logged = False
        reschedule_date: Optional[str] = None
        escalated_to_human = False
        final_status = "active"

        # Rule 1: Dispute Halt
        if intent == "dispute_charge":
            dispute_logged = True
            stopping_rule_triggered = True
            state = RecoveryState.DISPUTE_HALTED
            final_status = "dispute_logged"

        # Rule 2: Ghost Cutoff
        elif intent == "ghost_no_response":
            stopping_rule_triggered = True
            state = RecoveryState.GHOST_STOPPED
            final_status = "ghost_no_response"

        # Payment Agreements & Links
        elif intent == "agree_to_pay":
            amount_paise = cust.amount_due * 100
            link_raw = self.razorpay.generate_payment_link(
                customer_id=cust.customer_id,
                amount_paise=amount_paise,
                customer_name=cust.name,
                customer_phone=cust.phone,
                description=f"Razorpay recovery - {cust.persona_type}"
            )
            payment_link_info = PaymentLinkInfo(
                payment_link_id=link_raw["payment_link_id"],
                short_url=link_raw["short_url"],
                amount_inr=float(link_raw["amount_inr"]),
                status=link_raw.get("status", "created"),
                expires_at=link_raw.get("expires_at"),
                is_live_gateway=link_raw.get("is_live_gateway", False),
                simulated=link_raw.get("simulated", False),
                notes=link_raw.get("notes")
            )
            state = RecoveryState.LINK_ISSUED
            final_status = "commitment_and_link_issued"
            if turn_number >= max_turns:
                stopping_rule_triggered = True

        elif intent == "partial_payment_offer":
            partial_paise = (cust.amount_due // 2) * 100
            link_raw = self.razorpay.generate_payment_link(
                customer_id=cust.customer_id,
                amount_paise=partial_paise,
                customer_name=cust.name,
                customer_phone=cust.phone,
                description=f"Razorpay partial recovery - {cust.persona_type}"
            )
            payment_link_info = PaymentLinkInfo(
                payment_link_id=link_raw["payment_link_id"],
                short_url=link_raw["short_url"],
                amount_inr=float(link_raw["amount_inr"]),
                status=link_raw.get("status", "created"),
                expires_at=link_raw.get("expires_at"),
                is_live_gateway=link_raw.get("is_live_gateway", False),
                simulated=link_raw.get("simulated", False),
                notes=link_raw.get("notes")
            )
            state = RecoveryState.LINK_ISSUED
            final_status = "commitment_and_link_issued"
            if turn_number >= max_turns:
                stopping_rule_triggered = True

        elif intent == "reschedule_request":
            reschedule_date = "Coming Friday (11:00 AM IST)"
            state = RecoveryState.RESCHEDULED
            final_status = "rescheduled_promise_to_pay"
            if turn_number >= max_turns:
                stopping_rule_triggered = True

        elif intent == "payment_completed":
            state = RecoveryState.LINK_ISSUED
            final_status = "payment_settled_verified"
            stopping_rule_triggered = True

        elif intent == "link_issue_retry":
            amount_paise = cust.amount_due * 100
            link_raw = self.razorpay.generate_payment_link(
                customer_id=cust.customer_id,
                amount_paise=amount_paise,
                customer_name=cust.name,
                customer_phone=cust.phone,
                description=f"Razorpay recovery resend - {cust.persona_type}"
            )
            payment_link_info = PaymentLinkInfo(
                payment_link_id=link_raw["payment_link_id"],
                short_url=link_raw["short_url"],
                amount_inr=float(link_raw["amount_inr"]),
                status=link_raw.get("status", "created"),
                expires_at=link_raw.get("expires_at"),
                is_live_gateway=link_raw.get("is_live_gateway", False),
                simulated=link_raw.get("simulated", False),
                notes=link_raw.get("notes")
            )
            state = RecoveryState.LINK_ISSUED
            final_status = "link_reissued"

        elif intent in ["payment_method_query", "gratitude_close"]:
            if turn_number >= max_turns:
                stopping_rule_triggered = True

        elif intent == "aggressive_pushback":
            state = RecoveryState.DE_ESCALATED
            final_status = "deescalated_whatsapp_followup"
            if turn_number >= max_turns:
                stopping_rule_triggered = True

        # Rule 3: Max Turns Cutoff
        if turn_number >= max_turns and not stopping_rule_triggered:
            stopping_rule_triggered = True
            if state == RecoveryState.AWAITING_REPLY:
                state = RecoveryState.MAX_TURNS_REACHED
                final_status = "max_turns_exceeded"

        # Generate empathetic agent response
        short_url = payment_link_info.short_url if payment_link_info else None
        agent_move = self.llm.generate_agent_turn(
            customer_name=cust.name,
            amount_due=cust.amount_due,
            days_overdue=cust.days_overdue,
            conversation_history=conversation_history or [],
            detected_intent=intent,
            turn_number=turn_number,
            generated_link=short_url
        )

        return TurnDecision(
            turn=turn_number,
            customer_utterance=customer_utterance,
            detected_intent=intent,
            intent_confidence=confidence,
            sentiment=sentiment,
            agent_response=agent_move.get("response_text", ""),
            reasoning=agent_move.get("reasoning", ""),
            stopping_rule_triggered=stopping_rule_triggered,
            state=state,
            payment_link=payment_link_info,
            dispute_logged=dispute_logged,
            reschedule_date=reschedule_date,
            escalated_to_human=escalated_to_human,
            final_status=final_status
        )

    def run_full_session(self, customer: CustomerRecord) -> Dict[str, Any]:
        """
        Executes a complete multi-turn recovery session against the deterministic persona script.
        """
        history: List[Dict[str, Any]] = []
        turn = 1
        max_turns = customer.scoring_criteria.max_turns_allowed
        
        is_completed = False
        link_generated: Optional[Dict[str, Any]] = None
        commitment_obtained = False
        dispute_logged = False
        reschedule_date: Optional[str] = None
        escalated_to_human = False
        final_status = "unresolved"

        # Turn 1: Agent initial greeting
        agent_t1 = self.llm.generate_agent_turn(
            customer_name=customer.name,
            amount_due=customer.amount_due,
            days_overdue=customer.days_overdue,
            conversation_history=[],
            detected_intent="initial_outreach",
            turn_number=1
        )
        
        # Get customer turn 1 from deterministic script
        cust_reply_1 = customer.response_script.get("turn_1_initial", customer.response_script.get("default", "..."))
        intent_1 = self.classifier.classify(cust_reply_1)

        history.append({
            "turn": 1,
            "agent_utterance": agent_t1["response_text"],
            "agent_reasoning": agent_t1["reasoning"],
            "customer_utterance": cust_reply_1,
            "classified_intent": intent_1["intent"],
            "intent_confidence": intent_1["confidence"]
        })

        # Process Turn 1 state transitions & stopping rules
        if intent_1["intent"] == "ghost_no_response":
            final_status = "ghost_no_response"
            is_completed = True
        elif intent_1["intent"] == "dispute_charge":
            dispute_logged = True
            final_status = "dispute_logged"
            is_completed = True
        elif intent_1["intent"] in ["agree_to_pay", "partial_payment_offer"]:
            amount_to_bill = customer.amount_due if intent_1["intent"] == "agree_to_pay" else (customer.amount_due // 2)
            link_generated = self.razorpay.generate_payment_link(
                customer_id=customer.customer_id,
                amount_paise=amount_to_bill * 100,
                customer_name=customer.name,
                customer_phone=customer.phone,
                description=f"Razorpay recovery - {customer.persona_type}"
            )
            commitment_obtained = True
            final_status = "commitment_and_link_issued"
        elif intent_1["intent"] == "reschedule_request":
            reschedule_date = "Coming Friday (11:00 AM IST)"
            commitment_obtained = True
            final_status = "rescheduled_promise_to_pay"

        # Multi-turn continuation if needed
        if not is_completed and turn < max_turns:
            turn = 2
            short_url = link_generated.get("short_url") if link_generated else None
            agent_t2 = self.llm.generate_agent_turn(
                customer_name=customer.name,
                amount_due=customer.amount_due,
                days_overdue=customer.days_overdue,
                conversation_history=history,
                detected_intent=intent_1["intent"],
                turn_number=2,
                generated_link=short_url
            )
            
            # Select next scripted customer turn
            if dispute_logged:
                cust_reply_2 = customer.response_script.get("turn_2_dispute_ack", "Okay.")
            elif link_generated:
                cust_reply_2 = customer.response_script.get("turn_2_link_sent", customer.response_script.get("turn_2_partial_link", "Link mil gaya."))
            elif reschedule_date:
                cust_reply_2 = customer.response_script.get("turn_2_reschedule", "Theek hai.")
            elif intent_1["intent"] == "aggressive_pushback":
                cust_reply_2 = customer.response_script.get("turn_2_deescalate", "Theek hai message bhej do.")
                # Generate link for aggressive customer once de-escalated
                link_generated = self.razorpay.generate_payment_link(
                    customer_id=customer.customer_id,
                    amount_paise=customer.amount_due * 100,
                    customer_name=customer.name,
                    customer_phone=customer.phone
                )
                commitment_obtained = True
                final_status = "deescalated_link_issued"
            else:
                cust_reply_2 = customer.response_script.get("default", "Theek hai.")

            intent_2 = self.classifier.classify(cust_reply_2)
            history.append({
                "turn": 2,
                "agent_utterance": agent_t2["response_text"],
                "agent_reasoning": agent_t2["reasoning"],
                "customer_utterance": cust_reply_2,
                "classified_intent": intent_2["intent"],
                "intent_confidence": intent_2["confidence"]
            })
            is_completed = True

        return {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "amount_due": customer.amount_due,
            "persona_type": customer.persona_type,
            "outcome_ground_truth": customer.outcome_ground_truth,
            "turns_taken": len(history),
            "commitment_obtained": commitment_obtained,
            "link_generated": link_generated,
            "dispute_logged": dispute_logged,
            "reschedule_date": reschedule_date,
            "escalated_to_human": escalated_to_human,
            "final_status": final_status,
            "transcript_history": history
        }
