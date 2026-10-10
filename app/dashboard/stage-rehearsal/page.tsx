'use client';

import { StageSlider } from '@/components/dashboard/StageSlider';
import { TimetableGrid } from '@/components/dashboard/TimetableGrid';
import { AQIChart } from '@/components/charts/AQIChart';

export default function StageRehearsalPage() {
  return (
    <div className="container mx-auto px-4 md:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Stage Rehearsal & Timetable Simulator
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Simulation engine for testing schedule resilience under GRAP Stages I, II, III, and IV
        </p>
      </div>

      <StageSlider />
      <AQIChart />
      <TimetableGrid />
    </div>
  );
}
