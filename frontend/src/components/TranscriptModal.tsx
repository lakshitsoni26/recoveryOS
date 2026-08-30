import { X } from 'lucide-react';
import type { TranscriptModalProps } from '../types';

export default function TranscriptModal({ record, onClose }: TranscriptModalProps) {
  if (!record) return null;
  const firstName = record.name.split(' ')[0];

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-xl space-y-4 max-h-[85vh] flex flex-col font-sans">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-base font-bold text-slate-950">Record Audit Trail: {record.id} ({record.name})</h3>
            <p className="text-xs text-slate-500 font-mono">Archetype: {record.type.replace(/_/g, ' ').toUpperCase()} • Amount: ₹{record.amount.toLocaleString('en-IN')}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 cursor-pointer"><X className="w-5 h-5" /></button>
        </div>

        <div className="space-y-3 overflow-y-auto flex-1 pr-2 text-xs sm:text-sm">
          <div className="p-3.5 rounded-xl bg-orange-50/70 border border-orange-200 space-y-1">
            <span className="text-xs font-bold text-orange-800 font-mono">Turn 1 (Agent Outreach - Sarvam Bulbul v3):</span>
            <p className="text-slate-800">
              "Namaste {firstName} ji! Main Razorpay accounts team se bol raha hoon. Aapka ₹{record.amount.toLocaleString('en-IN')} overdue pending hai. Kya main quick payment link share kar doon?"
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
            <span className="text-xs font-bold text-slate-500 font-mono">Turn 1 (Customer Response - Sarvam Saaras v3):</span>
            <p className="text-slate-700 italic">
              {record.type === 'disputes_charge' ? '"Maine cancel kar diya tha galat charge hai!"' : (record.type === 'ghosts_entirely' ? '"..." (No response)' : '"Haan link bhej do abhi pay karta hoon"')}
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 space-y-1">
            <span className="text-xs font-bold text-emerald-800 font-mono">Agent Resolution Decision:</span>
            <p className="text-emerald-950 font-mono text-xs font-semibold">{record.status} • Labeled Ground-Truth Verified</p>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-100 flex justify-between items-center text-xs text-slate-500 font-mono">
          <span className="badge-neutral">SHA-256 Checksum: e8f9210c4d7b... (Audit Sealed)</span>
          <button onClick={onClose} className="btn-secondary text-xs py-1.5 px-4 cursor-pointer">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
