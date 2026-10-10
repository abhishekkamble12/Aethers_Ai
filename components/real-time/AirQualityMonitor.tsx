'use client';

import { motion } from 'framer-motion';
import { Activity, Radio, Gauge, Wind } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getAQIColor, getStageColor } from '@/lib/utils';

export function AirQualityMonitor() {
  const { data: aqiData, isConnected } = useWebSocket();

  return (
    <div className="glass-card p-5 space-y-4 border-slate-700/60">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
            <Radio className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-white text-base">Live CAAQMS Air Feed</h3>
        </div>

        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          <span className="text-xs text-slate-300 font-mono">
            {isConnected ? 'Live WebSocket' : 'Offline'}
          </span>
        </div>
      </div>

      {aqiData && (
        <motion.div
          key={aqiData.timestamp}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-3"
        >
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Current Delhi-NCR AQI</div>
              <div className={`text-3xl font-extrabold font-mono mt-0.5 ${getAQIColor(aqiData.aqi)}`}>
                {aqiData.aqi}
              </div>
            </div>

            <div className="text-right">
              <div className="text-xs text-slate-400">PM2.5 Level</div>
              <div className="text-xl font-bold font-mono text-white mt-0.5">
                {aqiData.pm25} <span className="text-xs font-normal text-slate-400">µg/m³</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800">
              <span className="text-slate-400">GRAP Stage:</span>
              <div className="mt-1">
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${getStageColor(aqiData.stage)}`}>
                  Stage {aqiData.stage}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800">
              <span className="text-slate-400">Exposure Avoided:</span>
              <div className="text-emerald-400 font-bold font-mono text-sm mt-0.5">
                {aqiData.exposureReduction}%
              </div>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 font-mono text-right">
            Station: {aqiData.station} • {aqiData.timestamp}
          </div>
        </motion.div>
      )}
    </div>
  );
}
