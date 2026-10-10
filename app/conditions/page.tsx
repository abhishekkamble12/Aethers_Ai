import { Activity, ShieldAlert, CheckCircle, Info, HeartPulse } from 'lucide-react';
import { STAGE_CONFIGS } from '@/lib/mockData';

export default function ConditionsPage() {
  return (
    <div className="container mx-auto px-4 md:px-6 py-12 max-w-4xl space-y-8">
      <div className="border-b border-slate-800 pb-6">
        <h1 className="text-3xl font-bold text-white tracking-tight">GRAP Air Quality Conditions & Rules</h1>
        <p className="text-sm text-slate-400 mt-2">
          Regulatory Action Rules for Delhi-NCR School Day Operations (Stages I to IV).
        </p>
      </div>

      <div className="space-y-6">
        {Object.values(STAGE_CONFIGS).map((stage) => (
          <div key={stage.stage} className="glass-card p-6 border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-extrabold text-xl text-white">{stage.name}</span>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {stage.aqiRange}
                </span>
              </div>

              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                Order {stage.orderCode}
              </span>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">
              {stage.reason}
            </p>

            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1.5">
                <HeartPulse className="w-3.5 h-3.5 text-rose-400" />
                Outdoor Activities: <strong className={stage.outdoorAllowed ? 'text-emerald-400' : 'text-rose-400'}>
                  {stage.outdoorAllowed ? 'ALLOWED (Advisory)' : 'SUSPENDED (Indoor Swaps Active)'}
                </strong>
              </span>

              <span>Deterministic Engine Priority: High</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
