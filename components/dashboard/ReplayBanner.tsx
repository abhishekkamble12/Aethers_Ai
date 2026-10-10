'use client';

import { motion } from 'framer-motion';
import { AlertTriangle, Cpu } from 'lucide-react';
import { useDashboardStore } from '@/store/dashboardStore';
import { STAGE_CONFIGS } from '@/lib/mockData';

export function ReplayBanner() {
  const { currentStage } = useDashboardStore();
  const stageInfo = STAGE_CONFIGS[currentStage];

  return (
    <div className="w-full bg-slate-900 border-b border-rose-500/30 px-4 py-3 text-xs">
      <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-sm">
                GRAP {stageInfo.name} Declared in Delhi-NCR
              </span>
              <span className="px-2 py-0.5 rounded font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                Order {stageInfo.orderCode}
              </span>
            </div>
            <p className="text-slate-300 text-xs mt-0.5">
              {stageInfo.reason}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded">
          <Cpu className="w-3.5 h-3.5" />
          <span>Deterministic Replay Active</span>
        </div>
      </div>
    </div>
  );
}
