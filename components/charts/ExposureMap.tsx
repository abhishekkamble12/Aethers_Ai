'use client';

import { MapPin, ShieldCheck } from 'lucide-react';
import { DELHI_ZONES } from '@/lib/mockData';
import { getAQIColor, getStageColor } from '@/lib/utils';

export function ExposureMap() {
  return (
    <div className="glass-card p-6 border-slate-800 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-emerald-500/20 text-emerald-400">
              <MapPin className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Delhi-NCR District Compliance Map
            </h2>
          </div>
          <p className="text-slate-300 text-xs">
            Compliance monitoring across 288 educational institutions in 6 Delhi-NCR zones
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded">
          <ShieldCheck className="w-4 h-4" />
          <span>99.2% District GRAP Compliance</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {DELHI_ZONES.map((zone) => (
          <div
            key={zone.id}
            className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-white text-sm">{zone.name}</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${getStageColor(zone.stage)}`}>
                Stage {zone.stage}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs pt-1">
              <div className="p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-400">Current AQI</span>
                <div className={`text-base font-bold font-mono ${getAQIColor(zone.aqi)}`}>
                  {zone.aqi}
                </div>
              </div>

              <div className="p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-400">Schools Active</span>
                <div className="text-base font-bold font-mono text-white">
                  {zone.schoolsCount} <span className="text-xs text-slate-400 font-normal">schools</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800">
              <span className="text-slate-400">Compliance Rate:</span>
              <span className="font-bold font-mono text-emerald-400">{zone.compliancePct}% Compliant</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
