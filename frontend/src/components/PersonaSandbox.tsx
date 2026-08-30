import { useState } from 'react';
import { Play, Sparkles } from 'lucide-react';
import type { PersonaSandboxProps, CustomPersonaPayload } from '../types';

export default function PersonaSandbox({ onLaunchCustomPersona }: PersonaSandboxProps) {
  const [name, setName] = useState<string>('Devendra Deshmukh');
  const [amount, setAmount] = useState<number | string>(9800);
  const [days, setDays] = useState<number | string>(21);
  const [personaType, setPersonaType] = useState<string>('willing_forgetful');
  const [reply, setReply] = useState<string>(
    'Haan sir main traveling tha isliye miss ho gaya. Link bhejiye abhi kar deta hoon.'
  );

  const handleLaunch = async () => {
    const numAmount = typeof amount === 'number' ? amount : parseInt(amount, 10) || 0;
    const numDays = typeof days === 'number' ? days : parseInt(days, 10) || 0;

    const payload: CustomPersonaPayload = {
      name,
      amount_due: numAmount,
      days_overdue: numDays,
      persona_type: personaType,
      opening_reply: reply
    };

    try {
      await fetch('/api/custom-persona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch {
      // Backend optional for local simulation
    }

    onLaunchCustomPersona(personaType, name, numAmount, numDays, reply);
  };

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <div className="text-xs font-bold font-mono text-orange-600 uppercase tracking-widest">Interactive Evaluation Sandbox</div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-950 font-sans tracking-tight">Create & Test Custom Persona</h2>
        <p className="text-slate-600 text-xs sm:text-sm mt-1">
          Inject custom overdue customer profiles into the live engine to test arbitrary edge cases and Hinglish negotiation responses.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="fintech-panel p-6 space-y-4">
          <h3 className="font-bold text-slate-950 text-sm sm:text-base">Customer Account Profile</h3>

          <div className="space-y-3.5 text-xs font-medium">
            <div>
              <label className="block text-slate-600 mb-1">Customer Full Name:</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 font-mono focus:outline-none focus:border-orange-500 shadow-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-600 mb-1">Amount Due (INR):</label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 font-mono focus:outline-none focus:border-orange-500 shadow-xs"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Days Overdue:</label>
                <input
                  type="number"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 font-mono focus:outline-none focus:border-orange-500 shadow-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-600 mb-1">Debtor Behavioral Archetype:</label>
              <select
                value={personaType}
                onChange={(e) => setPersonaType(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 font-mono focus:outline-none focus:border-orange-500 shadow-xs"
              >
                <option value="willing_forgetful">Willing & Forgetful (Prompt Payment)</option>
                <option value="disputes_charge">Disputes Charge (Stops at Rule #1)</option>
                <option value="genuinely_cant_pay">Genuinely Can't Pay (Promise-to-Pay)</option>
                <option value="ghosts_entirely">Ghost Customer (Stops at Rule #2)</option>
                <option value="aggressive">Aggressive Pushback (De-escalation)</option>
                <option value="partial_pay_willing">Partial Pay Willing (Installment Split)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-600 mb-1">Simulated Opening Reply (Hinglish):</label>
              <textarea
                rows={2}
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 font-mono focus:outline-none focus:border-orange-500 resize-none text-xs shadow-xs"
              />
            </div>

            <button
              onClick={handleLaunch}
              className="btn-primary w-full py-3 text-xs flex items-center justify-center gap-2 cursor-pointer mt-2"
            >
              <Play className="w-4 h-4 fill-white" /> Launch in Telephony Simulator
            </button>
          </div>
        </div>

        <div className="fintech-panel p-6 space-y-4">
          <h3 className="font-bold text-slate-950 text-sm sm:text-base flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-orange-600" /> State Machine Sandbox Rules
          </h3>
          <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <strong className="text-slate-950 font-mono block">1. Dispute Shield Activation</strong>
              <p className="text-slate-600">If the persona utters "cancel", "galat", "fraud", or "nahi liya", the state machine immediately transitions to DISPUTE_HALTED.</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <strong className="text-slate-950 font-mono block">2. Promise-to-Pay Gating</strong>
              <p className="text-slate-600">If the customer requests a delay, the engine negotiates a structured PTP date without sending payment links.</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <strong className="text-slate-950 font-mono block">3. Razorpay Payment Link Dispatch</strong>
              <p className="text-slate-600">If the customer confirms, the engine invokes Razorpay Test API and generates a verifiable short link.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
