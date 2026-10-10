'use client';

import { useState } from 'react';
import { UserCheck, Check, Clock, ShieldCheck } from 'lucide-react';

interface Teacher {
  id: string;
  name: string;
  role: string;
  assignedClass: string;
  status: 'ACKNOWLEDGED' | 'PENDING';
  assignedVenue: string;
}

export function TeacherRosterSection() {
  const [teachers, setTeachers] = useState<Teacher[]>([
    { id: 't1', name: 'Mr. Vikram Singh', role: 'PE Head Coach', assignedClass: '7A / 8A', status: 'ACKNOWLEDGED', assignedVenue: 'Indoor Gym 1' },
    { id: 't2', name: 'Ms. Ananya Sharma', role: 'Fitness Instructor', assignedClass: '7B / 9A', status: 'ACKNOWLEDGED', assignedVenue: 'Multipurpose Hall' },
    { id: 't3', name: 'Dr. Rajesh Verma', role: 'Senior Faculty', assignedClass: '6A', status: 'ACKNOWLEDGED', assignedVenue: 'Classroom 6A' },
    { id: 't4', name: 'Mrs. Sunita Kapoor', role: 'Lab Supervisor', assignedClass: '10A', status: 'PENDING', assignedVenue: 'Physics Lab 2' },
  ]);

  const toggleStatus = (id: string) => {
    setTeachers(prev => prev.map(t => t.id === id ? {
      ...t,
      status: t.status === 'ACKNOWLEDGED' ? 'PENDING' : 'ACKNOWLEDGED'
    } : t));
  };

  return (
    <div className="glass-card p-6 border-slate-800 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-emerald-500/20 text-emerald-400">
              <UserCheck className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Teacher Roster & Venue Allocation
            </h2>
          </div>
          <p className="text-slate-300 text-xs">
            Status of faculty assignments and indoor room allocations under Stage III
          </p>
        </div>

        <div className="text-xs font-mono px-3 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
          {teachers.filter(t => t.status === 'ACKNOWLEDGED').length} / {teachers.length} Acknowledged
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {teachers.map((teacher) => (
          <div
            key={teacher.id}
            className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-4"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">{teacher.name}</span>
                <span className="text-[11px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 font-mono border border-blue-500/20">
                  {teacher.assignedClass}
                </span>
              </div>
              <div className="text-xs text-slate-400">{teacher.role}</div>
              <div className="text-xs text-slate-300 font-mono flex items-center gap-1.5 pt-0.5">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
                <span>Venue: {teacher.assignedVenue}</span>
              </div>
            </div>

            <button
              onClick={() => toggleStatus(teacher.id)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
                teacher.status === 'ACKNOWLEDGED'
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20'
              }`}
            >
              {teacher.status === 'ACKNOWLEDGED' ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Acknowledged</span>
                </>
              ) : (
                <>
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  <span>Pending</span>
                </>
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
