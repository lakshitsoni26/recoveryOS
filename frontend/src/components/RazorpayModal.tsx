import { useState } from 'react';
import { X, QrCode, CreditCard, Building, Loader2, ExternalLink, CheckCircle2, Sparkles } from 'lucide-react';
import type { RazorpayModalProps, WebhookPaymentCapturedRequest } from '../types';

export default function RazorpayModal({
  isOpen,
  onClose,
  customer,
  paymentLink,
  onPaymentSuccess
}: RazorpayModalProps) {
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  if (!isOpen || !customer) return null;

  const actualLinkUrl = paymentLink?.short_url || 'https://rzp.io/rzp/gTXQ9yH';

  const triggerRazorpayCheckoutSDK = () => {
    if (typeof window !== 'undefined' && (window as any).Razorpay) {
      const options = {
        key: 'rzp_test_TWRvNyTicTORlc',
        amount: customer.amount * 100, // in paise
        currency: 'INR',
        name: 'RecoveryOS · Razorpay Recovery',
        description: `Delinquency clearance for ${customer.name} (#${customer.id})`,
        image: '/favicon.svg',
        handler: async function (response: any) {
          setIsProcessing(true);
          const paymentId = response.razorpay_payment_id || `pay_${Date.now()}`;
          const payload: WebhookPaymentCapturedRequest = {
            payment_link_id: paymentId,
            customer_id: customer.id,
            amount_inr: customer.amount,
            payment_method: 'upi'
          };
          try {
            await fetch('/api/webhook/payment-captured', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
          } catch {
            // Optional
          }
          setIsProcessing(false);
          onClose();
          if (onPaymentSuccess) onPaymentSuccess();
        },
        prefill: {
          name: customer.name,
          email: `${customer.name.toLowerCase().replace(/ /g, '')}@razorpayhacks.in`,
          contact: '+919876543210'
        },
        theme: {
          color: '#FF6600'
        },
        modal: {
          ondismiss: function () {
            console.log('Checkout modal closed by user');
          }
        }
      };

      try {
        const rzp = new (window as any).Razorpay(options);
        rzp.open();
        return;
      } catch (err) {
        console.error('Razorpay SDK init error:', err);
      }
    }

    // Fallback: Open payment page in new tab
    window.open(actualLinkUrl, '_blank');
  };

  const handleSimulateWebhook = async () => {
    setIsProcessing(true);
    const payload: WebhookPaymentCapturedRequest = {
      payment_link_id: paymentLink ? paymentLink.payment_link_id : 'plink_test_gTXQ9yH',
      customer_id: customer.id,
      amount_inr: customer.amount,
      payment_method: 'upi'
    };

    try {
      await fetch('/api/webhook/payment-captured', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch {
      // Backend webhook handler optional for frontend test flow
    }

    setTimeout(() => {
      setIsProcessing(false);
      onClose();
      if (onPaymentSuccess) onPaymentSuccess();
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4 font-sans">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-orange-600 flex items-center justify-center font-bold text-white text-base">₹</div>
            <div>
              <div className="text-sm font-bold text-slate-950">Razorpay Gateway (Live Test Mode)</div>
              <div className="text-xs text-slate-500 font-mono">Invoice Settlement for {customer.name}</div>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 cursor-pointer"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
          <span className="text-xs text-slate-600 font-bold uppercase tracking-wider">Amount Payable</span>
          <span className="text-2xl font-black text-emerald-700 font-mono">₹{customer.amount.toLocaleString('en-IN')}</span>
        </div>

        {/* Live Link Info Callout */}
        <div className="p-3.5 rounded-xl bg-orange-50/80 border border-orange-200 space-y-1.5 text-xs">
          <div className="text-[10.5px] font-mono font-bold text-orange-800 uppercase flex items-center justify-between">
            <span>Official Razorpay Payment Portal</span>
            <span className="text-emerald-700 font-bold">LIVE API v1</span>
          </div>
          <p className="text-slate-700 font-mono text-[11px] truncate">
            {actualLinkUrl}
          </p>
        </div>

        <div className="space-y-2">
          <div className="p-3.5 rounded-xl bg-orange-50/50 border border-orange-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <QrCode className="w-5 h-5 text-orange-600" />
              <div>
                <div className="text-xs font-bold text-slate-950">Instant UPI QR (GPay / PhonePe / Paytm)</div>
                <div className="text-[10.5px] text-slate-500">Zero MDR • Real-Time Webhook Settlement</div>
              </div>
            </div>
            <span className="text-[10px] font-bold text-orange-800 bg-white px-2 py-0.5 rounded border border-orange-200 font-mono">RECOMMENDED</span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-3 text-slate-500">
            <CreditCard className="w-5 h-5 text-slate-600" />
            <div>
              <div className="text-xs font-bold text-slate-800">Debit / Credit Cards</div>
              <div className="text-[10.5px]">Visa, Mastercard, RuPay, Amex</div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-3 text-slate-500">
            <Building className="w-5 h-5 text-slate-600" />
            <div>
              <div className="text-xs font-bold text-slate-800">Netbanking</div>
              <div className="text-[10.5px]">All 58 Indian Banks Supported</div>
            </div>
          </div>
        </div>

        {/* Primary Action Button: Launch Razorpay Standard Checkout SDK */}
        <button
          onClick={triggerRazorpayCheckoutSDK}
          disabled={isProcessing}
          className="btn-primary w-full py-3.5 text-xs justify-center font-bold disabled:opacity-50 cursor-pointer shadow-md"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Verifying Settlement with Razorpay...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Pay with Razorpay Standard Checkout (SDK) ⚡</span>
            </>
          )}
        </button>

        <div className="flex items-center gap-2 pt-1">
          <a
            href={actualLinkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 py-2 px-3 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>Open Link in Tab</span>
            <ExternalLink className="w-3 h-3" />
          </a>

          <button
            onClick={() => void handleSimulateWebhook()}
            className="flex-1 py-2 px-3 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Simulate Webhook</span>
          </button>
        </div>
      </div>
    </div>
  );
}
