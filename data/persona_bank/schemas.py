"""
Pydantic Schemas for the Persona Bank and Evaluation Pipeline.
Ensures strong typing, serialization, and deterministic validation.
"""
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field


PersonaType = Literal[
    "willing_forgetful",
    "disputes_charge",
    "genuinely_cant_pay",
    "ghosts_entirely",
    "aggressive",
    "partial_pay_willing"
]

GroundTruthOutcome = Literal[
    "pays_if_link_given",
    "dispute_logged_success",
    "reschedule_obtained",
    "ghost_logged_correct",
    "de_escalated",
    "partial_commitment"
]


class ScoringCriteria(BaseModel):
    must_generate_link: bool = Field(..., description="Whether a Razorpay link must be generated for full points")
    must_log_commitment: bool = Field(..., description="Whether a promise-to-pay date/commitment must be logged")
    must_log_dispute: bool = Field(False, description="Whether a dispute ticket must be created")
    must_escalate: bool = Field(False, description="Whether the conversation must be handed off to human agent")
    max_turns_allowed: int = Field(3, description="Maximum conversational turns before escalation or stopping")


class ContactAttempt(BaseModel):
    timestamp: str
    channel: str = "voice_hinglish"
    outcome: str
    notes: Optional[str] = None


class CustomerRecord(BaseModel):
    customer_id: str
    name: str
    phone: str
    preferred_language_mix: Literal["hinglish", "hindi_dominant", "english_dominant"]
    amount_due: int = Field(..., description="Amount due in INR")
    days_overdue: int
    payment_method_on_file: Literal["upi", "credit_card", "debit_card", "netbanking"]
    contact_history: List[ContactAttempt] = Field(default_factory=list)
    persona_type: PersonaType
    outcome_ground_truth: GroundTruthOutcome
    response_script: Dict[str, str] = Field(
        ..., 
        description="Deterministic response tree mapping conversational turns / agent actions to customer replies"
    )
    scoring_criteria: ScoringCriteria
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonaBank(BaseModel):
    version: str = "3.0.0"
    created_at: str
    description: str
    total_records: int
    distribution: Dict[PersonaType, int]
    records: List[CustomerRecord]
