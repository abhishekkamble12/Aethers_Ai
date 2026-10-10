'use client';

import { motion } from 'framer-motion';
import { ShieldCheck, Percent, Activity, Key, TrendingDown } from 'lucide-react';
import { getStageColor } from '@/lib/utils';
import { useWebSocket } from '@/hooks/useWebSocket';

interface KPICardsProps {
  peMinutesPreserved?: number;
  exposureAvoided?: number;
  currentStage?: number;
  auditHead?: string;
}

export function KPICards({
  peMinutesPreserved = 100,
  exposureAvoided = 84.5,
  currentStage = 3,
  auditHead = '3b9a7852c08e...'
}: KPICardsProps) {
  const { data: aqiData } = useWebSocket();
  const liveStage = aqiData?.stage || currentStage;
  const liveReduction = aqiData?.exposureReduction || exposureAvoided;

  const cards = [
    {
      title: 'Curriculum PE Preserved',
      value: `${peMinutesPreserved}%`,
      subtitle: 'Physical education curriculum maintained',
      icon: Percent,
      color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      badge: 'Active Schedule',
      badgeBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
    },
    {
      title: 'Exposure Mitigation',
      value: `${liveReduction}%`,
      subtitle: 'PM2.5 reduction via indoor swaps',
      icon: TrendingDown,
      color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      badge: 'Calculated Reduction',
      badgeBg: 'bg-blue-500/20 text-blue-300 border-blue-500/30'
    },
    {
      title: 'Active GRAP Stage',
      value: `Stage ${liveStage}`,
      subtitle: liveStage >= 3 ? 'Outdoor sports suspended' : 'Advisory Mode',
      icon: Activity,
      color: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      badge: `Order r-01${liveStage + 4}`,
      badgeBg: getStageColor(liveStage)
    },
    {
      title: 'Audit Block Head',
      value: auditHead,
      subtitle: 'WebCrypto SHA-256 ledger hash',
      icon: Key,
      color: 'bg-slate-700/50 text-slate-300 border-slate-600',
      badge: 'SHA-256 Validated',
      badgeBg: 'bg-slate-800 text-slate-300 border-slate-700'
    }
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.title}
            className="glass-card p-5 relative"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`w-9 h-9 rounded-lg border ${card.color} flex items-center justify-center`}>
                <Icon className="w-4 h-4" />
              </div>
              <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${card.badgeBg}`}>
                {card.badge}
              </span>
            </div>

            <div>
              <div className="text-2xl font-bold text-white font-mono tracking-tight mb-1">
                {card.value}
              </div>
              <div className="text-xs font-semibold text-slate-200">{card.title}</div>
              <p className="text-[11px] text-slate-400 mt-0.5">{card.subtitle}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
