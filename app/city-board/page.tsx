'use client';

import { ExposureMap } from '@/components/charts/ExposureMap';
import { AQIChart } from '@/components/charts/AQIChart';
import { AirQualityMonitor } from '@/components/real-time/AirQualityMonitor';

export default function CityBoardPage() {
  return (
    <div className="container mx-auto px-4 md:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Delhi-NCR District City Board & Air Safety Monitor
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          District-wide real-time air quality dashboard and GRAP compliance oversight across all education zones
        </p>
      </div>

      <ExposureMap />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <AQIChart />
        </div>
        <div>
          <AirQualityMonitor />
        </div>
      </div>
    </div>
  );
}
