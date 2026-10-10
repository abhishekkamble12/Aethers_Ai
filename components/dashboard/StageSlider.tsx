'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sliders, CheckCircle2, ShieldAlert, Cpu } from 'lucide-react';
import { useDashboardStore } from '@/store/dashboardStore';
import { useStageSimulation } from '@/hooks/useStageSimulation';
import { GRAPStageNumber } from '@/types/dashboard';

export function StageSlider() {
  const { currentStage, setStage, setSchedule } = useDashboardStore();
  const { simulateStage, simulation, isLoading } = useStageSimulation();

  const stages = [
    { value: 1 as GRAPStageNumber, label: 'Stage I', range: '201-300 AQI', color: 'text-yellow-300' },
    { value: 2 as GRAPStageNumber, label: 'Stage II', range: '301-400 AQI', color: 'text-orange-300' },
    { value: 3 as GRAPStageNumber, label: 'Stage III', range: '401-450 AQI', color: 'text-red-300' },
    { value: 4 as GRAPStageNumber, label: 'Stage IV', range: '>450 AQI', color: 'text-slate-300' },
  ];

  useEffect(() => {
    simulateStage(currentStage);
  }, [currentStage]);

  useEffect(() => {
    if (simulation) {
      setSchedule(simulation.planBSchedule);
    }
  }, [simulation]);

  const handleStageChange = (newStage: GRAPStageNumber) => {
    setStage(newStage);
  };

  return (
    <div className="glass-card p-6 border-slate-800 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-blue-500/20 text-blue-400">
              <Sliders className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Stage Rehearsal Simulator
            </h2>
          </div>
          <p className="text-slate-300 text-xs">
            Adjust the declared GRAP stage to observe real-time schedule adjustments.
          </p>
        </div>
        <div className="status-indicator text-xs self-start sm:self-center">
          <Cpu className="w-3.5 h-3.5" />
          <span>Rules Evaluation Engine</span>
        </div>
      </div>

      {/* Stage Selection Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stages.map((stage) => {
          const isSelected = currentStage === stage.value;
          return (
            <div
              key={stage.value}
              onClick={() => handleStageChange(stage.value)}
              className={`cursor-pointer p-3.5 rounded-lg border text-center transition-colors ${
                isSelected
                  ? 'bg-blue-950/60 border-blue-500'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <span className={`font-bold text-sm ${stage.color}`}>{stage.label}</span>
                {isSelected && <CheckCircle2 className="w-4 h-4 text-blue-400" />}
              </div>
              <div className="text-[11px] text-slate-400 font-mono">{stage.range}</div>
            </div>
          );
        })}
      </div>

      {/* Slider */}
      <div className="px-1">
        <input
          type="range"
          min="1"
          max="4"
          step="1"
          value={currentStage}
          onChange={(e) => handleStageChange(Number(e.target.value) as GRAPStageNumber)}
          className="w-full h-2 bg-slate-800 rounded-lg slider appearance-none accent-blue-600 cursor-pointer"
        />
        <div className="flex justify-between text-[11px] text-slate-400 font-mono mt-2">
          <span>Stage I (Advisory)</span>
          <span>Stage II (Reschedule)</span>
          <span>Stage III (Suspension)</span>
          <span>Stage IV (Hybrid)</span>
        </div>
      </div>

      {/* Simulation Result */}
      {isLoading ? (
        <div className="flex items-center justify-center py-4 bg-slate-900/60 rounded-lg border border-slate-800 text-xs text-slate-400">
          Evaluating GRAP rules and schedule parameters...
        </div>
      ) : simulation ? (
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-blue-500/10 text-blue-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <div className="text-slate-400">Affected Outdoor Classes</div>
              <div className="text-sm font-bold text-white font-mono">
                {simulation.affectedClassesCount} Classes Rescheduled
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div>
              <div className="text-slate-400">Curriculum Preservation</div>
              <div className="text-sm font-bold text-emerald-400 font-mono">
                {simulation.peMinutesPreserved}% Preserved
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-slate-800 text-slate-300">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <div className="text-slate-400">Calculated Exposure Avoided</div>
              <div className="text-sm font-bold text-slate-200 font-mono">
                {simulation.exposureReductionPct}% Mitigation
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
