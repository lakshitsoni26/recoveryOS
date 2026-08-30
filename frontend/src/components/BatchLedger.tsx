import { useState } from 'react';
import { Download, RefreshCw, Search } from 'lucide-react';
import type { BatchLedgerProps, CustomerRecord } from '../types';

export default function BatchLedger({
  records,
  onSelectRecord,
  onRunBatch,
  isRunningBatch
}: BatchLedgerProps) {
  const [search, setSearch] = useState<string>('');

  const filtered: CustomerRecord[] = records.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.type.toLowerCase().includes(search.toLowerCase()) ||
      r.id.toLowerCase().includes(search.toLowerCase())
  );

  const exportCSV = () => {
    let csv = 'Customer_ID,Name,Persona_Type,Amount_INR,Days_Overdue,Status,Simulated_Recovered\n';
    records.forEach((r) => {
      csv += `${r.id},"${r.name}",${r.type},${r.amount},${r.days},${r.status},${r.recovered}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `razorpay_recovery_batch_50_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <div className="text-xs font-bold font-mono text-orange-600 uppercase tracking-widest">Ground-Truth Audit Matrix</div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-950 font-sans tracking-tight">50-Record Batch Evaluation Ledger</h2>
          <p className="text-slate-600 text-xs sm:text-sm mt-1">
            Deterministic multi-turn personas. Click any row to inspect the full transcript and SHA-256 integrity seal.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter name, ID, archetype..."
              className="pl-9 pr-3.5 py-2 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-orange-500 placeholder:text-slate-400 shadow-xs"
            />
          </div>
          <button
            onClick={exportCSV}
            className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
          <button
            onClick={onRunBatch}
            disabled={isRunningBatch}
            className="btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRunningBatch ? 'animate-spin' : ''}`} /> Re-Run Eval
          </button>
        </div>
      </div>

      <div className="fintech-panel overflow-hidden">
        <div className="overflow-x-auto max-h-[580px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200 font-mono">
              <tr>
                <th className="px-5 py-3.5">Account ID</th>
                <th className="px-5 py-3.5">Customer Name</th>
                <th className="px-5 py-3.5">Persona Archetype</th>
                <th className="px-5 py-3.5">Amount Due</th>
                <th className="px-5 py-3.5">Overdue</th>
                <th className="px-5 py-3.5">Resolution Outcome</th>
                <th className="px-5 py-3.5 text-right">Audit Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs font-sans">
              {filtered.map((r, i) => (
                <tr
                  key={r.id || i}
                  onClick={() => onSelectRecord(r)}
                  className="hover:bg-orange-50/40 transition-colors cursor-pointer"
                >
                  <td className="px-5 py-3.5 font-mono text-orange-700 font-bold">{r.id}</td>
                  <td className="px-5 py-3.5 font-bold text-slate-950">{r.name}</td>
                  <td className="px-5 py-3.5">
                    <span className="px-2 py-0.5 rounded text-[10.5px] font-mono font-bold bg-slate-100 text-slate-700 uppercase border border-slate-200">
                      {r.type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-950">
                    ₹{r.amount.toLocaleString('en-IN')}
                  </td>
                  <td className="px-5 py-3.5 text-slate-500 font-mono">{r.days} days</td>
                  <td className="px-5 py-3.5">
                    {r.recovered ? (
                      <span className="px-2.5 py-0.5 rounded text-[10.5px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono">
                        RECOVERED (₹{r.amount.toLocaleString('en-IN')})
                      </span>
                    ) : r.status === 'dispute_logged' ? (
                      <span className="px-2.5 py-0.5 rounded text-[10.5px] font-bold bg-red-50 text-red-700 border border-red-200 font-mono">
                        DISPUTE HALTED (RULE #1)
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 rounded text-[10.5px] font-bold bg-slate-100 text-slate-700 border border-slate-300 font-mono">
                        GHOST STOPPED (RULE #2)
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button className="px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-[10.5px] font-mono text-orange-700 border border-slate-200 font-semibold cursor-pointer">
                      SHA256 Seal →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
