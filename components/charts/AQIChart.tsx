'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { LineChart as LineChartIcon } from 'lucide-react';
import { HOURLY_AQI_TREND } from '@/lib/mockData';

export function AQIChart() {
  const stageThresholds = [
    { y: 200, label: 'Stage I (201+)', color: '#fde047' },
    { y: 300, label: 'Stage II (301+)', color: '#fdba74' },
    { y: 400, label: 'Stage III (401+)', color: '#fca5a5' },
    { y: 450, label: 'Stage IV (>450)', color: '#cbd5e1' },
  ];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="glass-card p-3 border-slate-700 bg-slate-900 text-xs space-y-1">
          <p className="text-white font-bold">{label} PM2.5 Forecast</p>
          <p className="text-blue-400 font-mono">AQI Level: {data.aqi}</p>
          <p className="text-emerald-400 font-mono">PM2.5: {data.pm25} µg/m³</p>
          <p className="text-amber-300 font-semibold">GRAP Stage {data.stage}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-card p-6 border-slate-800 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-blue-500/20 text-blue-400">
              <LineChartIcon className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              24-Hour Air Quality & PM2.5 Diurnal Trend
            </h2>
          </div>
          <p className="text-slate-300 text-xs">
            Forecasted PM2.5 curves used by deterministic engine to identify clean air swap slots
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          {stageThresholds.map((t) => (
            <div key={t.y} className="flex items-center gap-1.5 font-mono text-[11px]">
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: t.color }} />
              <span className="text-slate-300">{t.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="h-64 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={HOURLY_AQI_TREND}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[100, 500]} />
            <Tooltip content={<CustomTooltip />} />

            {stageThresholds.map((t) => (
              <ReferenceLine
                key={t.y}
                y={t.y}
                stroke={t.color}
                strokeDasharray="3 3"
                strokeOpacity={0.5}
              />
            ))}

            <Line
              type="monotone"
              dataKey="aqi"
              stroke="#3b82f6"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#3b82f6' }}
            />
            <Line
              type="monotone"
              dataKey="pm25"
              stroke="#10b981"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={{ r: 3, fill: '#10b981' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
