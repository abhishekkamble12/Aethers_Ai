'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldCheck, Wind, LayoutDashboard, Sliders, CheckCircle2, Building2 } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getStageColor } from '@/lib/utils';

function HeaderNav() {
  const pathname = usePathname();

  const navItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Stage Rehearsal', href: '/dashboard/stage-rehearsal', icon: Sliders },
    { label: 'Proof Verification', href: '/verification', icon: ShieldCheck },
    { label: 'District City Board', href: '/city-board', icon: Building2 },
  ];

  return (
    <nav className="hidden md:flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname?.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              isActive
                ? 'bg-blue-600 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function Header() {
  const { data: aqiData, isConnected } = useWebSocket();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
      <div className="container mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
        {/* Logo & Brand */}
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <Wind className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">
                  Saans
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                  साँस v2.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                GRAP Air Safety Day Planner
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation Links */}
        <Suspense fallback={<div className="hidden md:block w-80 h-8 bg-slate-900 rounded-lg animate-pulse" />}>
          <HeaderNav />
        </Suspense>

        {/* Right Status Indicator */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <div className="text-xs">
              <span className="text-slate-400">AQI: </span>
              <span className="font-bold text-slate-100">{aqiData?.aqi || 415}</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getStageColor(aqiData?.stage || 3)}`}>
              Stage {aqiData?.stage || 3}
            </span>
          </div>

          <Link
            href="/verification"
            className="btn-primary text-xs py-1.5 px-3 hidden lg:flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Verify SHA-256</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
