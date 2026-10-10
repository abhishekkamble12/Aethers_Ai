'use client';

import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Move, ArrowRightLeft, CalendarCheck, ShieldCheck } from 'lucide-react';
import confetti from 'canvas-confetti';
import { TimetableEntry } from '@/types/dashboard';
import { useDashboardStore } from '@/store/dashboardStore';

interface TimetableGridProps {
  schedule?: TimetableEntry[];
  onApprove?: (plan: 'A' | 'B') => void;
}

export function TimetableGrid({ schedule, onApprove }: TimetableGridProps) {
  const { schedule: storeSchedule, setSchedule, selectedPlan, setSelectedPlan, approvePlan, isApproved, approvedPlan } = useDashboardStore();
  const currentSchedule = schedule || storeSchedule;

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return;

    const newItems = Array.from(currentSchedule);
    const [reorderedItem] = newItems.splice(result.source.index, 1);
    newItems.splice(result.destination.index, 0, reorderedItem);

    setSchedule(newItems);
  };

  const handleApprovalSubmit = (plan: 'A' | 'B') => {
    approvePlan(plan);
    if (onApprove) onApprove(plan);

    try {
      confetti({
        particleCount: 60,
        spread: 60,
        origin: { y: 0.6 }
      });
    } catch {
      // Confetti fallback
    }
  };

  const getStatusBadge = (classification: string) => {
    switch (classification) {
      case 'BANNED':
        return 'bg-rose-500/10 text-rose-300 border-rose-500/30';
      case 'ADVISORY':
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30';
      case 'ALLOWED':
        return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
      default:
        return 'bg-slate-500/10 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <div className="glass-card p-6 border-slate-800 space-y-6">
      {/* Section Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-blue-500/20 text-blue-400">
              <CalendarCheck className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Timetable Schedule Optimization
            </h2>
          </div>
          <p className="text-slate-300 text-xs">
            GRAP Stage III Directive suspends outdoor activities. Re-order slots or approve Plan A / B strategy.
          </p>
        </div>

        {/* Action Approval Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleApprovalSubmit('A')}
            className={`btn-success text-xs py-2 px-3 ${
              isApproved && approvedPlan === 'A' ? 'ring-2 ring-emerald-400' : ''
            }`}
          >
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>Approve Plan A (Swaps)</span>
          </button>

          <button
            onClick={() => handleApprovalSubmit('B')}
            className={`btn-teal text-xs py-2 px-3 ${
              isApproved && approvedPlan === 'B' ? 'ring-2 ring-teal-400' : ''
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Approve Plan B (Indoor)</span>
          </button>
        </div>
      </div>

      {/* Plan Strategy Selection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div
          onClick={() => setSelectedPlan('A')}
          className={`p-4 rounded-lg cursor-pointer border transition-colors ${
            selectedPlan === 'A'
              ? 'bg-slate-900 border-emerald-500'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <span>Plan A: Clean Air Time Swaps</span>
              {selectedPlan === 'A' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            </h3>
            <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono border border-emerald-500/20">
              82% Exposure Reduction
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Re-align outdoor sports slots to afternoon periods (P7/P8) when forecasted PM2.5 levels subside.
          </p>
        </div>

        <div
          onClick={() => setSelectedPlan('B')}
          className={`p-4 rounded-lg cursor-pointer border transition-colors ${
            selectedPlan === 'B'
              ? 'bg-slate-900 border-teal-500'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <span>Plan B: Indoor Wellness Sessions</span>
              {selectedPlan === 'B' && <CheckCircle2 className="w-4 h-4 text-teal-400" />}
            </h3>
            <span className="text-[11px] px-2 py-0.5 rounded bg-teal-500/10 text-teal-300 font-mono border border-teal-500/20">
              100% PE Preserved
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Convert outdoor physical education to indoor air-filtered sports (Chess, Table Tennis, Yoga, Ergometrics).
          </p>
        </div>
      </div>

      {/* Approval Confirmation Alert */}
      <AnimatePresence>
        {isApproved && (
          <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-500/40 flex items-center gap-3 text-emerald-200 text-xs">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>
              <span className="font-bold text-white">Plan {approvedPlan} Approved & Digitally Signed</span>
              <p className="text-[11px] text-emerald-300/90 mt-0.5">
                Principal signature digest registered into SHA-256 audit chain log. Parent advisories dispatched.
              </p>
            </div>
          </div>
        )}
      </AnimatePresence>

      {/* Draggable Timetable Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/80">
        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="timetable-droppable">
            {(provided) => (
              <table
                ref={provided.innerRef}
                {...provided.droppableProps}
                className="w-full text-left text-xs"
              >
                <thead className="bg-slate-950 text-slate-300 border-b border-slate-800 font-semibold">
                  <tr>
                    <th className="p-3 w-8 text-center"></th>
                    <th className="p-3">Class</th>
                    <th className="p-3">Period & Time</th>
                    <th className="p-3">Original Activity</th>
                    <th className="p-3">Forecast PM2.5</th>
                    <th className="p-3">Order Classification</th>
                    <th className="p-3">Optimized Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {currentSchedule.map((item, index) => (
                    <Draggable key={item.id} draggableId={item.id} index={index}>
                      {(dragProvided, dragSnapshot) => (
                        <tr
                          ref={dragProvided.innerRef}
                          {...dragProvided.draggableProps}
                          className={`transition-colors ${
                            dragSnapshot.isDragging ? 'bg-slate-800 border-y border-blue-500/40' : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <td className="p-3 text-center" {...dragProvided.dragHandleProps}>
                            <Move className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300 cursor-grab mx-auto" />
                          </td>
                          <td className="p-3 font-bold text-white">{item.class}</td>
                          <td className="p-3 text-slate-300">
                            <div className="font-semibold text-slate-200">{item.period}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{item.time}</div>
                          </td>
                          <td className="p-3 text-slate-300">
                            <div>{item.originalActivity}</div>
                            <div className="text-[11px] text-slate-400">{item.teacher}</div>
                          </td>
                          <td className="p-3 font-mono">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              item.forecastPM25 > 400 ? 'bg-rose-500/15 text-rose-300' : 'bg-amber-500/15 text-amber-300'
                            }`}>
                              {item.forecastPM25} µg/m³
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getStatusBadge(item.orderClassification)}`}>
                              {item.orderClassification}
                            </span>
                          </td>
                          <td className="p-3 text-slate-200">
                            <div className="font-medium text-slate-100">{item.optimizedAction}</div>
                            {item.venue && (
                              <div className="text-[11px] text-slate-400 font-mono mt-0.5">Venue: {item.venue}</div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </tbody>
              </table>
            )}
          </Droppable>
        </DragDropContext>
      </div>
    </div>
  );
}
