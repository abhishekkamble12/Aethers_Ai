'use client';

import { TeacherRosterSection } from '@/components/dashboard/TeacherRosterSection';
import { NotificationCenter } from '@/components/real-time/NotificationCenter';

export default function TeacherRosterPage() {
  return (
    <div className="container mx-auto px-4 md:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Faculty Roster & Communication Hub
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Manage teacher room reallocations and parent advisory broadcasts
        </p>
      </div>

      <TeacherRosterSection />
      <NotificationCenter />
    </div>
  );
}
