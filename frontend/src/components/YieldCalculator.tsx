import { useState } from 'react';
import { Calculator } from 'lucide-react';

export default function YieldCalculator() {
  const [overdueAmount, setOverdueAmount] = useState<number>(2500000); // 25 Lakhs default
  const [agencyRate, setAgencyRate] = useState<number>(12); // 12% industry avg
  const [agencyFeePct, setAgencyFeePct] = useState<number>(25); // 25% collection fee

  const recoveryOsRate = 54.5;
  const recoveryOsRecovered = Math.round(overdueAmount * (recoveryOsRate / 100));
  const agencyRecovered = Math.round(overdueAmount * (agencyRate / 100));
  const agencyFeesPaid = Math.round(agencyRecovered * (agencyFeePct / 100));
  const agencyNetCash = agencyRecovered - agencyFeesPaid;

  const recoveryOsCost = 15000; // Flat SaaS tier estimation
  const recoveryOsNetCash = recoveryOsRecovered - recoveryOsCost;
  const netAddedCapital = recoveryOsNetCash - agencyNetCash;
  const roiMultiple = ((netAddedCapital / recoveryOsCost)).toFixed(1);

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <div className="text-xs font-bold font-mono text-orange-600 uppercase tracking-widest">Revenue Projection Engine</div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-950 font-sans tracking-tight mt-1">Merchant Recovery Yield Simulator</h2>
        <p className="text-slate-600 text-xs sm:text-sm mt-1">
          Model how much trapped capital RecoveryOS recovers compared to traditional outsourced debt collection agencies.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Sliders Input Panel (7 Cols) */}
        <div className="lg:col-span-7 fintech-panel p-6 space-y-6">
          <h3 className="font-bold text-sm text-slate-950 flex items-center gap-2">
            <Calculator className="w-4 h-4 text-orange-600" />
            <span>Interactive Portfolio Parameters</span>
          </h3>

          {/* Slider 1: Monthly Overdue Volume */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-700">Monthly Overdue Invoices (INR):</label>
              <span className="font-mono font-bold text-base text-orange-600">
                ₹{(overdueAmount / 100000).toFixed(1)} Lakhs ({overdueAmount.toLocaleString('en-IN')})
              </span>
            </div>
            <input
              type="range"
              min="200000"
              max="10000000"
              step="100000"
              value={overdueAmount}
              onChange={(e) => setOverdueAmount(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>₹2L (Seed)</span>
              <span>₹25L (Growth)</span>
              <span>₹1 Cr (Enterprise)</span>
            </div>
          </div>

          {/* Slider 2: Current Agency Recovery Rate */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-700">Current Recovery Rate (%):</label>
              <span className="font-mono font-bold text-sm text-slate-900">{agencyRate}% (Industry Avg: 12%)</span>
            </div>
            <input
              type="range"
              min="5"
              max="30"
              step="1"
              value={agencyRate}
              onChange={(e) => setAgencyRate(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-700"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>5% (Low)</span>
              <span>12% (Typical)</span>
              <span>30% (Best Case)</span>
            </div>
          </div>

          {/* Slider 3: Agency Contingency Fee */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-700">Agency Commission / Fee (%):</label>
              <span className="font-mono font-bold text-sm text-slate-900">{agencyFeePct}% on recovered cash</span>
            </div>
            <input
              type="range"
              min="10"
              max="40"
              step="1"
              value={agencyFeePct}
              onChange={(e) => setAgencyFeePct(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-700"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>10%</span>
              <span>25% (Standard)</span>
              <span>40%</span>
            </div>
          </div>

          {/* 3 Summary Stats */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-center font-mono">
              <p className="text-[10px] text-slate-500 font-semibold uppercase">Recovery Win-Rate</p>
              <p className="text-base font-bold text-emerald-700 mt-1">54.5%</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-center font-mono">
              <p className="text-[10px] text-slate-500 font-semibold uppercase">Manual Hours Saved</p>
              <p className="text-base font-bold text-blue-700 mt-1">140 hrs/mo</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-center font-mono">
              <p className="text-[10px] text-slate-500 font-semibold uppercase">Net ROI Multiple</p>
              <p className="text-base font-bold text-orange-600 mt-1">{roiMultiple}x</p>
            </div>
          </div>
        </div>

        {/* Head-to-Head Comparison Card (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="fintech-panel p-6 space-y-4 bg-emerald-50/50 border border-emerald-300">
            <div className="flex justify-between items-center pb-3 border-b border-emerald-200">
              <div>
                <p className="font-mono text-[10.5px] uppercase font-bold text-emerald-800 tracking-wider">PROJECTED MONTHLY CASHFLOW</p>
                <h4 className="text-xs text-slate-600">RecoveryOS vs Traditional Agency</h4>
              </div>
              <span className="badge-green">54.5% RATE</span>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between items-center p-3 rounded-xl bg-white border border-emerald-200 shadow-xs">
                <div>
                  <span className="text-slate-500 text-[11px] block">RecoveryOS Recovered</span>
                  <span className="text-xl font-black text-emerald-700">₹{recoveryOsRecovered.toLocaleString('en-IN')}</span>
                </div>
                <span className="text-xs font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">54.5% Win</span>
              </div>

              <div className="flex justify-between items-center p-3 rounded-xl bg-white border border-slate-200">
                <div>
                  <span className="text-slate-400 text-[11px] block">Agency Net (After {agencyFeePct}% fee)</span>
                  <span className="text-base font-bold text-slate-700">₹{agencyNetCash.toLocaleString('en-IN')}</span>
                </div>
                <span className="text-xs text-slate-500 font-medium">{agencyRate}% Win</span>
              </div>

              <div className="p-4 rounded-xl bg-orange-500 text-white space-y-1 shadow-md">
                <div className="text-[10px] uppercase tracking-wider font-bold opacity-90">NET EXTRA CASH RECOVERED</div>
                <div className="text-2xl sm:text-3xl font-black">+₹{netAddedCapital.toLocaleString('en-IN')}</div>
                <div className="text-[11px] opacity-90">Directly settled into merchant Razorpay virtual account</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
