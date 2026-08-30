export default function FunnelAnalytics() {
  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <div className="text-xs font-bold font-mono text-orange-600 uppercase tracking-widest">Observability & Cohorts</div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-950 font-sans tracking-tight">Conversion Funnel & Recovery Velocity</h2>
        <p className="text-slate-600 text-xs sm:text-sm mt-1">Deep analytics across persona archetypes, conversion drop-offs, and turn velocity.</p>
      </div>

      <div className="fintech-panel p-6 sm:p-7 space-y-5">
        <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-500">4-Stage Measured Revenue Funnel</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 text-center font-mono">
          <div className="metric-card bg-slate-50 border border-slate-200">
            <div className="text-[11px] text-slate-500 font-bold">1. CONTACTED</div>
            <div className="text-2xl font-black text-slate-950 mt-1">50 Records</div>
            <div className="text-[11px] text-slate-500 mt-1">₹4,06,700 (100%)</div>
          </div>
          <div className="metric-card bg-blue-50/50 border border-blue-200">
            <div className="text-[11px] text-blue-700 font-bold">2. COMMITMENT</div>
            <div className="text-2xl font-black text-blue-700 mt-1">28 Records</div>
            <div className="text-[11px] text-blue-600 mt-1">₹2,58,700 (56.0%)</div>
          </div>
          <div className="metric-card bg-orange-50/50 border border-orange-200">
            <div className="text-[11px] text-orange-700 font-bold">3. ACTION ISSUED</div>
            <div className="text-2xl font-black text-orange-700 mt-1">18 Records</div>
            <div className="text-[11px] text-orange-600 mt-1">Razorpay Links (36.0%)</div>
          </div>
          <div className="metric-card bg-emerald-50/70 border border-emerald-300">
            <div className="text-[11px] text-emerald-800 font-bold">4. RECOVERED (SIM)</div>
            <div className="text-2xl font-black text-emerald-800 mt-1">28 Records</div>
            <div className="text-[11px] text-emerald-700 font-bold mt-1">₹2,21,700 (54.5%)</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="fintech-panel p-6 space-y-4">
          <h4 className="font-bold text-slate-950 text-sm sm:text-base">Archetype Recovery Conversion</h4>
          <div className="space-y-3.5 font-mono text-xs">
            <div>
              <div className="flex justify-between text-slate-700 mb-1">
                <span>Willing Forgetful (15 accounts)</span> <span className="text-emerald-700 font-bold">100% (15/15)</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100"><div className="h-full bg-emerald-500 rounded-full w-full" /></div>
            </div>
            <div>
              <div className="flex justify-between text-slate-700 mb-1">
                <span>Can't Pay / Reschedule (10 accounts)</span> <span className="text-blue-700 font-bold">100% PTP (10/10)</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100"><div className="h-full bg-blue-500 rounded-full w-full" /></div>
            </div>
            <div>
              <div className="flex justify-between text-slate-700 mb-1">
                <span>Partial Pay (3 accounts)</span> <span className="text-orange-700 font-bold">100% Partial (3/3)</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100"><div className="h-full bg-orange-500 rounded-full w-full" /></div>
            </div>
            <div>
              <div className="flex justify-between text-slate-700 mb-1">
                <span>Disputes Halted (10 accounts)</span> <span className="text-red-700 font-bold">0% Cash / 100% Gated</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100"><div className="h-full bg-red-400 rounded-full w-0" /></div>
            </div>
            <div>
              <div className="flex justify-between text-slate-700 mb-1">
                <span>Ghosts Cutoff (8 accounts)</span> <span className="text-slate-500 font-bold">0% Cash / 100% Rule #2</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100"><div className="h-full bg-slate-400 rounded-full w-0" /></div>
            </div>
          </div>
        </div>

        <div className="fintech-panel p-6 space-y-4">
          <h4 className="font-bold text-slate-950 text-sm sm:text-base">Key Operating Metrics</h4>
          <div className="grid grid-cols-2 gap-3 text-center font-mono">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-500 font-semibold">AVG TURNS TO RESOLVE</div>
              <div className="text-xl font-bold text-orange-600 mt-1">1.8 Turns</div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-500 font-semibold">AVG CALL DURATION</div>
              <div className="text-xl font-bold text-emerald-700 mt-1">42 Seconds</div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-500 font-semibold">UNEARNED FALSE WINS</div>
              <div className="text-xl font-bold text-slate-950 mt-1">0 (Zero)</div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[10px] text-slate-500 font-semibold">GATEWAY IDEMPOTENCY</div>
              <div className="text-xl font-bold text-blue-700 mt-1">100% Valid</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
