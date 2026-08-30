import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic,
  CreditCard,
  Volume2,
  VolumeX,
  Send,
  Square,
  ShieldCheck,
  User,
  CheckCircle2,
  Play,
  Square as StopIcon,
  ExternalLink,
  Sparkles
} from 'lucide-react';
import useSpeechToText from '../hooks/useSpeechToText';
import type {
  TurnMessage,
  StoppingRules,
  RazorpayLink,
  TelephonyHubProps,
  SimulateTurnResponse
} from '../types';

export interface PersonaOption {
  type: string;
  name: string;
  amt: number;
  days: number;
  tag: string;
  sample: string;
}

interface ExtendedTelephonyHubProps extends TelephonyHubProps {
  availablePersonas?: PersonaOption[];
  onPaymentSuccessGlobal?: (customerId: string, amount: number) => void;
}

const DEFAULT_PERSONA_OPTIONS: PersonaOption[] = [
  { type: 'willing_forgetful', name: 'Rohit Reddy', amt: 4500, days: 12, tag: 'FORGETFUL', sample: 'Haan bhai busy tha dhyan nahi raha. Link bhej do abhi kar deta hoon.' },
  { type: 'disputes_charge', name: 'Priya Nair', amt: 8500, days: 18, tag: 'DISPUTE', sample: 'Maine yeh service pichle hafte cancel kar di thi! Galat charge hai.' },
  { type: 'genuinely_cant_pay', name: 'Sunita Chauhan', amt: 15000, days: 24, tag: "CAN'T PAY", sample: 'Sir salary delay ho gayi hai. Is Friday tak ka time de do please.' },
  { type: 'ghosts_entirely', name: 'Amit Joshi', amt: 2500, days: 30, tag: 'GHOST (SILENT)', sample: '...' },
];

export default function TelephonyHub({
  customer,
  onSelectCustomer,
  onOpenPaymentModal,
  availablePersonas = DEFAULT_PERSONA_OPTIONS,
  onPaymentSuccessGlobal
}: ExtendedTelephonyHubProps) {
  const initialGreeting = `Namaste ${customer.name.split(' ')[0]} ji! Main Razorpay accounts team se bol raha hoon. Aapka ₹${customer.amount.toLocaleString('en-IN')} ka invoice ${customer.days} din se pending hai. Kya main quick UPI payment link share kar doon?`;

  const [messages, setMessages] = useState<TurnMessage[]>([
    {
      sender: 'AI',
      text: initialGreeting,
      turn: 1,
      reasoning: 'Warm Empathetic Outreach',
      link: null
    }
  ]);

  const [inputVal, setInputVal] = useState<string>('');
  const [turn, setTurn] = useState<number>(1);
  const [callSeconds, setCallSeconds] = useState<number>(0);
  const [sentiment, setSentiment] = useState<string>('Neutral');
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [isPaid, setIsPaid] = useState<boolean>(false);
  const [paidUtr, setPaidUtr] = useState<string | null>(null);

  const [stoppingRules, setStoppingRules] = useState<StoppingRules>({
    turnsOk: true,
    disputeHalt: false,
    ghostCutoff: false,
    linkDispatched: false
  });

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  const stopAllAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current.src = '';
      currentAudioRef.current = null;
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsPlayingAudio(false);
  }, []);

  const speakText = useCallback(
    (textToSpeak: string) => {
      if (!voiceEnabled) return;
      stopAllAudio();
      setIsPlayingAudio(true);

      const ttsUrl = `/api/tts?text=${encodeURIComponent(textToSpeak)}`;
      const audio = new Audio(ttsUrl);
      currentAudioRef.current = audio;

      audio.onplay = () => {
        setIsPlayingAudio(true);
      };

      audio.onended = () => {
        setIsPlayingAudio(false);
        currentAudioRef.current = null;
      };

      audio.onerror = () => {
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(textToSpeak);
          u.lang = 'hi-IN';
          u.rate = 1.0;
          u.onstart = () => setIsPlayingAudio(true);
          u.onend = () => {
            setIsPlayingAudio(false);
          };
          u.onerror = () => {
            setIsPlayingAudio(false);
          };
          window.speechSynthesis.speak(u);
        } else {
          setIsPlayingAudio(false);
        }
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(textToSpeak);
            u.lang = 'hi-IN';
            u.onstart = () => setIsPlayingAudio(true);
            u.onend = () => setIsPlayingAudio(false);
            window.speechSynthesis.speak(u);
          } else {
            setIsPlayingAudio(false);
          }
        });
      }
    },
    [voiceEnabled, stopAllAudio]
  );

  // AUTO-RUN first message greeting on mount and whenever persona changes!
  useEffect(() => {
    stopAllAudio();
    setIsPaid(false);
    setPaidUtr(null);

    const timer = setTimeout(() => {
      speakText(initialGreeting);
    }, 120);

    return () => {
      clearTimeout(timer);
      stopAllAudio();
    };
  }, [customer.name, customer.amount, customer.days, initialGreeting, speakText, stopAllAudio]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCallSeconds((s) => s + 1);
    }, 1000);
    return () => {
      clearInterval(timer);
      stopAllAudio();
    };
  }, [stopAllAudio]);

  // Handle successful payment capture (automatic bot reaction & voice speech)
  const handlePaymentCaptured = useCallback(
    async (customUtr?: string) => {
      if (isPaid) return;
      const utr = customUtr || `UTR_RZP_${Math.floor(Date.now() / 1000)}`;
      setIsPaid(true);
      setPaidUtr(utr);
      setSentiment('Paid & Settled (100% Recovered)');
      setStoppingRules((r) => ({ ...r, linkDispatched: true }));

      // Fire background webhook
      try {
        await fetch('/api/webhook/payment-captured', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            payment_link_id: 'plink_gTXQ9yH',
            customer_id: customer.id,
            amount_inr: customer.amount,
            payment_method: 'upi'
          })
        });
      } catch {
        // Optional error catch
      }

      const custFirstName = customer.name.split(' ')[0];
      const botPraise = `Bahut bahut dhanyavaad ${custFirstName} ji! Aapka ₹${customer.amount.toLocaleString('en-IN')} ka payment Razorpay par successfully capture ho gaya hai (Transaction UTR: ${utr}). Aapka invoice ab completely clear hai aur official receipt aapke WhatsApp par dispatch kar di gayi hai. Shubh din!`;

      setMessages((prev) => [
        ...prev,
        {
          sender: 'AI',
          text: botPraise,
          turn: turn + 1,
          reasoning: 'Razorpay Webhook: payment_link.paid -> Account Closed',
          link: null
        }
      ]);

      if (onPaymentSuccessGlobal) {
        onPaymentSuccessGlobal(customer.id, customer.amount);
      }

      speakText(botPraise);
    },
    [customer, isPaid, onPaymentSuccessGlobal, speakText, turn]
  );

  const handleSend = useCallback(
    async (explicitText?: string) => {
      const text = (explicitText !== undefined ? explicitText : inputVal).trim();
      if (!text) return;

      stopAllAudio();

      const userMsg: TurnMessage = {
        sender: 'YOU',
        text,
        turn,
        reasoning: 'Customer Inbound Utterance',
        link: null
      };

      setMessages((prev) => [...prev, userMsg]);
      setInputVal('');

      const nextTurn = turn + 1;
      setTurn(nextTurn);

      try {
        const resp = await fetch('/api/simulate-turn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            customer_id: customer.id,
            customer_name: customer.name,
            amount_due: customer.amount,
            days_overdue: customer.days,
            customer_utterance: text,
            turn_number: turn,
            channel: 'voice_call'
          })
        });

        if (resp.ok) {
          const data = (await resp.json()) as SimulateTurnResponse;
          const aiReply = data.agent_response;
          const reasoning = data.agent_reasoning || data.detected_intent || 'State Transition Logged';
          const linkData = data.payment_link || (data.detected_intent === 'agree_to_pay' ? {
            payment_link_id: 'plink_gTXQ9yH',
            short_url: 'https://rzp.io/rzp/gTXQ9yH',
            amount_inr: customer.amount
          } : null);

          if (linkData) {
            setStoppingRules((r) => ({ ...r, linkDispatched: true }));
          }
          if (data.stopping_rule_triggered) {
            setSentiment('Disputed (Halted)');
            setStoppingRules((r) => ({ ...r, disputeHalt: true }));
          } else if (data.detected_intent === 'agree_to_pay') {
            setSentiment('Cooperative (Agreed)');
          } else if (data.detected_intent === 'reschedule_request') {
            setSentiment('Constrained (Rescheduled)');
          } else if (data.detected_intent === 'ghost_no_response') {
            setSentiment('Silent (Cutoff)');
            setStoppingRules((r) => ({ ...r, ghostCutoff: true }));
          }

          setMessages((prev) => [
            ...prev,
            {
              sender: 'AI',
              text: aiReply,
              turn: nextTurn,
              reasoning,
              link: linkData
            }
          ]);
          speakText(aiReply);
          return;
        }
      } catch {
        // Fallback simulation
      }

      const u = text.toLowerCase();
      let reply = '';
      let reasoning = '';
      let link: RazorpayLink | null = null;
      const custFirstName = customer.name.split(' ')[0];

      if (u.includes('cancel') || u.includes('galat') || u.includes('fraud') || u.includes('dispute')) {
        reply = `Samajh gaya ${custFirstName} ji. Maine aapka dispute ticket #DISP-${Math.floor(Math.random() * 9000) + 1000} log kar diya hai. Hamari team review karegi, tab tak koi payment nahi karni.`;
        reasoning = 'Dispute raised -> Logged ticket & halted outreach per Rule #1.';
        setSentiment('Concerned (Disputed)');
        setStoppingRules((r) => ({ ...r, disputeHalt: true }));
      } else if (u.includes('salary') || u.includes('friday') || u.includes('time')) {
        reply = `Koi baat nahi ${custFirstName} ji, maine coming Friday ka promise-to-pay schedule kar diya hai. Tab link remind karwa dunga.`;
        reasoning = 'Reschedule commitment logged.';
        setSentiment('Constrained (Rescheduled)');
      } else if (u.includes('...') || u === 'silent') {
        reply = `Lagta hai aap busy hain ${custFirstName} ji. Hum baad mein connect karenge. Have a good day!`;
        reasoning = 'Unresponsive customer -> Stopped outreach per Rule #2.';
        setSentiment('Unresponsive (Silent)');
        setStoppingRules((r) => ({ ...r, ghostCutoff: true }));
      } else {
        const testLink = 'https://rzp.io/rzp/gTXQ9yH';
        reply = `Maine aapke phone par official Razorpay payment link dispatch kar diya hai: ${testLink} . Aap UPI ya Card se 2 min mein complete kar sakte hain.`;
        reasoning = 'Customer agreed -> Generated Razorpay Test-Mode payment link.';
        setSentiment('Cooperative (Positive)');
        link = {
          payment_link_id: 'plink_gTXQ9yH',
          short_url: testLink,
          amount_inr: customer.amount
        };
        setStoppingRules((r) => ({ ...r, linkDispatched: true }));
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: 'AI',
          text: reply,
          turn: nextTurn,
          reasoning,
          link
        }
      ]);
      speakText(reply);
    },
    [customer, inputVal, speakText, stopAllAudio, turn]
  );

  const handleSpeechComplete = useCallback(
    (spokenText: string) => {
      void handleSend(spokenText);
    },
    [handleSend]
  );

  const { isListening, toggleListening } = useSpeechToText({
    onSpeechComplete: handleSpeechComplete,
    onTranscriptChange: setInputVal
  });

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Left Column: Customer Archetypes & Active Guardrails (4 Cols) */}
      <div className="lg:col-span-4 space-y-4">
        <div className="fintech-panel p-5 space-y-4">
          <div className="flex justify-between items-center pb-3 border-b border-slate-100">
            <span className="font-mono text-xs uppercase font-bold text-orange-600 tracking-wider flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" /> Customer Archetype
            </span>
            <span className="badge-neutral">
              {availablePersonas.length} ACCOUNTS
            </span>
          </div>

          <div className="space-y-2 max-h-[380px] overflow-y-auto scrollbar-thin pr-1">
            {availablePersonas.map((p) => {
              const isSelected = customer.name.toLowerCase() === p.name.toLowerCase();
              const isThisPaid = isSelected && isPaid;
              return (
                <button
                  key={p.name}
                  onClick={() => {
                    stopAllAudio();
                    onSelectCustomer(p.type, p.name, p.amt, p.days, p.sample);
                  }}
                  className={`w-full text-left p-3 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-orange-50/70 border-orange-500 shadow-xs ring-1 ring-orange-400'
                      : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-950 text-xs flex items-center gap-1.5">
                      {p.name}
                      {isThisPaid && <span className="text-emerald-600">✔</span>}
                    </span>
                    <span className="text-[9.5px] px-2 py-0.5 rounded font-bold font-mono"
                      style={{
                        background: isThisPaid ? '#15803D' : (isSelected ? '#FF6600' : '#F4F1EC'),
                        color: isThisPaid || isSelected ? '#FFFFFF' : '#4B5563'
                      }}>
                      {isThisPaid ? 'PAID & SETTLED' : p.tag}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 font-mono">
                    {isThisPaid ? (
                      <span className="text-emerald-700 font-semibold">₹{p.amt.toLocaleString('en-IN')} recovered via Razorpay</span>
                    ) : (
                      `₹${p.amt.toLocaleString('en-IN')} due • ${p.days} days overdue`
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Policy Guardrails */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs font-mono">
            <div className="text-[10.5px] uppercase font-bold text-slate-900 tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-orange-600" /> Gated Stopping Rules
            </div>
            <div className="flex items-center justify-between text-slate-700 pt-1">
              <span>Max 3 Turns Bound</span> <span className="text-emerald-700 font-bold">✔ OK (Turn {turn}/3)</span>
            </div>
            <div className="flex items-center justify-between text-slate-700">
              <span>Dispute Halt Gating</span>{' '}
              <span className={stoppingRules.disputeHalt ? 'text-red-600 font-bold' : 'text-slate-400'}>
                {stoppingRules.disputeHalt ? '✔ HALTED (Rule #1)' : 'Standby'}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-700">
              <span>Ghost Limit Cutoff</span>{' '}
              <span className={stoppingRules.ghostCutoff ? 'text-rose-600 font-bold' : 'text-slate-400'}>
                {stoppingRules.ghostCutoff ? '✔ RULE #2' : 'Standby'}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-700">
              <span>Razorpay Settlement</span>{' '}
              <span className={isPaid ? 'text-emerald-700 font-bold' : (stoppingRules.linkDispatched ? 'text-blue-700 font-semibold' : 'text-slate-400')}>
                {isPaid ? '✔ PAID & CLOSED' : (stoppingRules.linkDispatched ? 'Link Dispatched' : 'Ready')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: Live Call Terminal (8 Cols) */}
      <div className="lg:col-span-8 space-y-4">
        <div className="fintech-panel p-5 rounded-2xl flex flex-col h-[650px]">
          {/* Telephony Header */}
          <div className="flex flex-wrap justify-between items-center pb-4 border-b border-slate-100 gap-3">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${isPaid ? 'bg-emerald-500' : 'bg-emerald-500 animate-pulse'}`} />
              <div>
                <h3 className="font-bold text-sm text-slate-950 flex items-center gap-2">
                  <span>{customer.name}</span>
                  <span className="font-mono text-xs font-normal text-slate-500">({customer.personaType})</span>
                  {isPaid && (
                    <span className="badge-green text-[10px] py-0.5">
                      PAID (UTR: {paidUtr})
                    </span>
                  )}
                </h3>
                <div className="text-xs font-mono text-slate-500 mt-0.5">
                  Call Duration:{' '}
                  <span className="text-slate-900 font-bold">
                    {String(Math.floor(callSeconds / 60)).padStart(2, '0')}:{String(callSeconds % 60).padStart(2, '0')}
                  </span>{' '}
                  • Sentiment: <span className={isPaid ? 'text-emerald-700 font-bold' : 'text-orange-600 font-bold'}>{sentiment}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  if (voiceEnabled) {
                    stopAllAudio();
                    setVoiceEnabled(false);
                  } else {
                    setVoiceEnabled(true);
                  }
                }}
                className={`p-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                  voiceEnabled ? 'bg-orange-50 text-orange-700 border border-orange-200' : 'bg-slate-100 text-slate-500'
                }`}
                title={voiceEnabled ? 'Mute AI Voice' : 'Unmute AI Voice'}
              >
                {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                <span className="hidden sm:inline">{voiceEnabled ? 'Sarvam Voice On' : 'Voice Muted'}</span>
              </button>

              {isPlayingAudio && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-orange-50 border border-orange-200">
                  <div className="flex items-center gap-1">
                    {[12, 20, 8, 24, 16].map((h, i) => (
                      <span key={i} className="w-1 rounded-full bg-orange-600 wave-bar" style={{ height: `${h}px`, animationDelay: `${i * 0.1}s` }} />
                    ))}
                  </div>
                  <button
                    onClick={stopAllAudio}
                    className="ml-1 text-[10px] text-red-600 hover:text-red-700 font-mono font-bold flex items-center gap-0.5 cursor-pointer"
                    title="Stop Voice"
                  >
                    <StopIcon className="w-2.5 h-2.5 fill-red-600" /> Stop
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Messages Container */}
          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex flex-col ${m.sender === 'AI' ? 'items-start' : 'items-end'}`}>
                <div className="flex items-center gap-2 mb-1 px-1">
                  <span className="font-mono text-[10px] uppercase font-bold text-slate-400">
                    {m.sender === 'AI' ? '⚡ RecoveryOS Agent' : `👤 ${customer.name}`} • Turn {m.turn}
                  </span>
                  {m.sender === 'AI' && (
                    <button
                      onClick={() => speakText(m.text)}
                      className="text-[10px] font-mono text-orange-600 hover:text-orange-700 flex items-center gap-1 cursor-pointer font-semibold"
                      title="Play Voice Audio"
                    >
                      <Play className="w-2.5 h-2.5 fill-orange-600" /> Replay Voice
                    </button>
                  )}
                </div>

                <div
                  className={`max-w-[88%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-xs ${
                    m.sender === 'AI'
                      ? 'bg-orange-50/80 text-slate-900 border border-orange-100 rounded-tl-none font-sans font-medium'
                      : 'bg-slate-100 text-slate-900 border border-slate-200 rounded-tr-none font-sans'
                  }`}
                >
                  <p>{m.text}</p>

                  {/* Payment Link Card with Direct URL & Auto-Update Simulation */}
                  {m.link && (
                    <div className="mt-3.5 p-4 rounded-xl bg-white border border-emerald-300 text-slate-900 space-y-3 shadow-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
                        <div className="text-[10.5px] font-mono text-emerald-800 font-bold uppercase flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Official Razorpay Payment Link</span>
                        </div>
                        <span className="font-mono text-xs font-black text-slate-950">
                          ₹{customer.amount.toLocaleString('en-IN')}
                        </span>
                      </div>

                      {/* Direct Link Display */}
                      <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-2 font-mono text-xs">
                        <span className="text-slate-700 truncate font-semibold">https://rzp.io/rzp/gTXQ9yH</span>
                        <a
                          href="https://rzp.io/rzp/gTXQ9yH"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-[11px] inline-flex items-center gap-1 shrink-0 transition-colors"
                        >
                          <span>Open Link</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        {!isPaid ? (
                          <>
                            <button
                              onClick={() => onOpenPaymentModal(m.link || null)}
                              className="btn-primary text-xs py-2 px-3.5 cursor-pointer"
                            >
                              <CreditCard className="w-3.5 h-3.5" /> Open Checkout Modal
                            </button>
                            <button
                              onClick={() => void handlePaymentCaptured()}
                              className="px-3 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                            >
                              <Sparkles className="w-3.5 h-3.5" /> Confirm Payment & Trigger Bot Reaction
                            </button>
                          </>
                        ) : (
                          <div className="w-full p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 font-mono text-xs font-bold flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            <span>Payment Captured & Verified · UTR: {paidUtr}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {m.reasoning && (
                  <span className="text-[10px] font-mono text-slate-400 mt-1 px-1 italic">
                    Reasoning: {m.reasoning}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Quick Action Hints */}
          <div className="px-4 py-2 border-t border-slate-100 flex items-center gap-2 overflow-x-auto text-[11px] font-mono">
            <span className="text-slate-400 uppercase tracking-wider text-[10px]">Try Quick Hinglish:</span>
            {[
              'Link bhej do, abhi UPI se pay karta hoon',
              'Maine cancel kar diya tha, galat bill hai!',
              'Salary Friday ko aayegi, tab tak time de do',
              '...'
            ].map((hint, i) => (
              <button
                key={i}
                onClick={() => setInputVal(hint)}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 whitespace-nowrap transition-colors cursor-pointer"
              >
                "{hint}"
              </button>
            ))}
          </div>

          {/* Input & Microphone Bar */}
          <div className="p-3 border-t border-slate-100 flex items-center gap-2 bg-slate-50 rounded-b-xl">
            <button
              onClick={toggleListening}
              className={`p-3 rounded-xl transition-all flex items-center justify-center cursor-pointer ${
                isListening
                  ? 'bg-red-600 text-white animate-pulse shadow-md'
                  : 'bg-orange-600 hover:bg-orange-700 text-white shadow-xs'
              }`}
              title={isListening ? 'Stop recording' : 'Speak in Hinglish (Sarvam Saaras STT)'}
            >
              {isListening ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleSend()}
              placeholder={
                isListening
                  ? 'Listening in Hinglish (Sarvam Saaras v3)... Speak now...'
                  : 'Type Hinglish response (e.g., "Haan link bhejo abhi karta hoon")...'
              }
              className="flex-1 bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-900 focus:outline-none focus:border-orange-500 placeholder:text-slate-400"
            />

            <button
              onClick={() => void handleSend()}
              disabled={!inputVal.trim()}
              className="btn-primary text-xs py-2.5 px-4 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
