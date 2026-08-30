import { Home, Phone, Database, BarChart3, UserPlus, Calculator, Play } from 'lucide-react';
import type { NavbarProps } from '../types';

export default function Navbar({ activeTab, setActiveTab, onRunBatch, isRunningBatch }: NavbarProps) {
  const isTabActive = (tab: string) => {
    if (tab === 'telephony' && (activeTab === 'telephony' || activeTab === 'simulator')) return true;
    if (tab === 'calculator' && (activeTab === 'calculator' || activeTab === 'roi')) return true;
    return activeTab === tab;
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-[#0B132B]/95 backdrop-blur-md border-b border-white/[0.08] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-6">
        {/* Left: Brand Identity */}
        <div
          className="flex items-center gap-3 cursor-pointer select-none group shrink-0"
          onClick={() => setActiveTab('home')}
        >
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-sm shadow-md shadow-blue-600/30 group-hover:bg-blue-500 transition-colors">
            ₹
          </div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-sm sm:text-base text-white tracking-tight">
              Razorpay <span className="text-blue-400">RecoveryOS</span>
            </span>
            <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-md bg-blue-500/15 text-blue-300 border border-blue-500/30 font-mono font-semibold">
              TRACK 3
            </span>
          </div>
        </div>

        {/* Center: Clean Floating Navigation Links (No Clunky Grey Pill Box) */}
        <nav className="hidden md:flex items-center gap-1 text-xs font-semibold text-slate-300">
          <button
            onClick={() => setActiveTab('home')}
            className={`px-3.5 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
              isTabActive('home')
                ? 'bg-blue-600/20 text-blue-300 font-bold border border-blue-500/30'
                : 'hover:text-white hover:bg-white/5'
            }`}
          >
            <Home className="w-3.5 h-3.5" /> Overview
          </button>
          <button
            onClick={() => setActiveTab('telephony')}
            className={`px-3.5 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
              isTabActive('telephony')
                ? 'bg-blue-600 text-white font-bold shadow-sm'
                : 'hover:text-white hover:bg-white/5'
            }`}
          >
            <Phone className="w-3.5 h-3.5" /> Telephony Hub
          </button>
          <button
            onClick={() => setActiveTab('batch')}
            className={`px-3.5 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
              isTabActive('batch')
                ? 'bg-blue-600 text-white font-bold shadow-sm'
                : 'hover:text-white hover:bg-white/5'
            }`}
          >
            <Database className="w-3.5 h-3.5" /> 50-Record Batch
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-3.5 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
              isTabActive('analytics')
                ? 'bg-blue-600 text-white font-bold shadow-sm'
                : 'hover:text-white hover:bg-white/5'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" /> Funnel Analytics
          </button>
          <button
            onClick={() => setActiveTab('sandbox')}
            className={`px-3.5 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
              isTabActive('sandbox')
                ? 'bg-blue-600 text-white font-bold shadow-sm'
                : 'hover:text-white hover:bg-white/5'
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" /> Sandbox
          </button>
          <button
            onClick={() => setActiveTab('calculator')}
            className={`px-3.5 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
              isTabActive('calculator')
                ? 'bg-blue-600 text-white font-bold shadow-sm'
                : 'hover:text-white hover:bg-white/5'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" /> ROI Calculator
          </button>
        </nav>

        {/* Right: Action & Gateway Status */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden xl:flex items-center gap-2 text-[11px] font-mono text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Gateway Active</span>
          </div>

          <button
            onClick={onRunBatch}
            disabled={isRunningBatch}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md shadow-blue-600/20 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-white" />
            <span>{isRunningBatch ? 'Evaluating...' : 'Run 50-Record Eval'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
