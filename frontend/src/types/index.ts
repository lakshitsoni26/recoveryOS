/**
 * Razorpay AI Revenue Recovery - Type Definitions
 */

export type PersonaType =
  | 'willing_forgetful'
  | 'disputes_charge'
  | 'genuinely_cant_pay'
  | 'ghosts_entirely'
  | 'aggressive'
  | 'partial_pay_willing'
  | string;

export type ResolutionStatus =
  | 'commitment_and_link_issued'
  | 'dispute_logged'
  | 'rescheduled_promise_to_pay'
  | 'ghost_no_response'
  | string;

export interface CustomerRecord {
  id: string;
  name: string;
  type: PersonaType;
  amount: number;
  days: number;
  status: ResolutionStatus;
  recovered: boolean;
}

export type BatchRecord = CustomerRecord;

export interface CustomerState {
  id: string;
  name: string;
  amount: number;
  days: number;
  personaType: PersonaType;
}

export interface RazorpayLink {
  payment_link_id: string;
  short_url: string;
  amount_inr: number;
}

export interface TurnMessage {
  sender: 'AI' | 'YOU';
  text: string;
  turn: number;
  reasoning?: string;
  link?: RazorpayLink | null;
}

export interface StoppingRules {
  turnsOk: boolean;
  disputeHalt: boolean;
  ghostCutoff: boolean;
  linkDispatched: boolean;
}

export interface FunnelStageMetrics {
  records: number;
  amount_inr: number;
  percentage: number;
}

export interface FunnelMetrics {
  stage_1_contacted: FunnelStageMetrics;
  stage_2_commitment: FunnelStageMetrics;
  stage_3_action_issued: FunnelStageMetrics;
  stage_4_recovered_simulated: FunnelStageMetrics;
}

export interface BatchRunResponse {
  funnel: FunnelMetrics;
  failure_and_non_cash_breakdown: Record<string, number>;
  records: Array<{
    account_id: string;
    customer_name: string;
    persona_type: string;
    amount_inr: number;
    days_overdue: number;
    ground_truth_status: string;
    recovered: boolean;
    turns_taken: number;
    audit_sha256: string;
  }>;
}

export interface SimulateTurnRequest {
  customer_id: string;
  customer_name: string;
  amount_due: number;
  days_overdue: number;
  customer_utterance: string;
  turn_number: number;
}

export interface SimulateTurnResponse {
  turn?: number;
  customer_utterance?: string;
  detected_intent?: string;
  sentiment?: string;
  agent_response: string;
  agent_reasoning?: string;
  stopping_rule_triggered?: boolean;
  payment_link?: RazorpayLink | null;
}

export interface WebhookPaymentCapturedRequest {
  payment_link_id: string;
  customer_id: string;
  amount_inr: number;
  payment_method?: 'upi' | 'card' | 'netbanking' | string;
}

export interface CustomPersonaPayload {
  name: string;
  amount_due: number;
  days_overdue: number;
  persona_type: string;
  opening_reply: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  gateway_mode: string;
  sarvam_tts_ready: boolean;
  active_campaign: string;
}

export interface PersonasResponse {
  version: string;
  total_records: number;
  distribution: Record<string, number>;
  records: CustomerRecord[];
}

export type TabType = 'home' | 'telephony' | 'batch' | 'analytics' | 'sandbox' | 'calculator';

export interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onRunBatch: () => void;
  isRunningBatch: boolean;
}

export interface TelephonyHubProps {
  customer: CustomerState;
  onSelectCustomer: (type: string, name: string, amount: number, days: number, sampleReply: string) => void;
  onOpenPaymentModal: (link: RazorpayLink | null) => void;
  paymentLink?: RazorpayLink | null;
}

export interface BatchLedgerProps {
  records: CustomerRecord[];
  onSelectRecord: (record: CustomerRecord) => void;
  onRunBatch: () => void;
  isRunningBatch: boolean;
}

export interface PersonaSandboxProps {
  onLaunchCustomPersona: (type: string, name: string, amount: number, days: number, sampleReply: string) => void;
}

export interface RazorpayModalProps {
  isOpen: boolean;
  onClose: () => void;
  customer: CustomerState | null;
  paymentLink: RazorpayLink | null;
  onPaymentSuccess?: () => void;
}

export interface TranscriptModalProps {
  record: CustomerRecord | null;
  onClose: () => void;
}

export interface UseSpeechToTextOptions {
  onSpeechComplete?: (transcript: string) => void;
  onTranscriptChange?: (transcript: string) => void;
  lang?: string;
}

export interface UseSpeechToTextReturn {
  isListening: boolean;
  transcript: string;
  error: string | null;
  startListening: () => Promise<void>;
  stopListening: () => void;
  toggleListening: () => void;
  setTranscript: (text: string) => void;
}
