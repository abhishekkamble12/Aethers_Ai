'use client';

import { ReplayBanner } from '@/components/dashboard/ReplayBanner';
import { KPICards } from '@/components/dashboard/KPICards';
import { StageSlider } from '@/components/dashboard/StageSlider';
import { TimetableGrid } from '@/components/dashboard/TimetableGrid';
import { TeacherRosterSection } from '@/components/dashboard/TeacherRosterSection';
import { AQIChart } from '@/components/charts/AQIChart';
import { NotificationCenter } from '@/components/real-time/NotificationCenter';
import { HashChainVerifier } from '@/components/verification/HashChainVerifier';
import { AirQualityMonitor } from '@/components/real-time/AirQualityMonitor';

export default function DashboardPage() {
  return (
    <div className="min-h-screen space-y-8 pb-12">
      {/* Replay Status Banner */}
      <ReplayBanner />

      <main className="container mx-auto px-4 md:px-6 space-y-8">
        {/* KPI Summary Cards */}
        <KPICards />

        {/* Live Air Quality Monitor & 24h Trend Chart Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <AQIChart />
          </div>
          <div>
            <AirQualityMonitor />
          </div>
        </div>

        {/* Interactive Stage Rehearsal Simulator */}
        <StageSlider />

        {/* Timetable Optimization Grid with Drag-and-Drop & Plan A/B Swaps */}
        <TimetableGrid />

        {/* Bilingual WhatsApp & SMS Parent Notification Center */}
        <NotificationCenter />

        {/* Teacher Roster & Venue Allocation Section */}
        <TeacherRosterSection />

        {/* Cryptographic Hash Chain Verifier */}
        <HashChainVerifier />
      </main>
    </div>
  );
}
