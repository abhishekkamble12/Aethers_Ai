'use client';

import Link from 'next/link';
import { Bot, Shield, FileText, Scale, ExternalLink } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 py-8 text-xs text-slate-400">
      <div className="container mx-auto px-4 md:px-6 space-y-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <span className="font-bold text-slate-200 text-sm">Saans (साँस)</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">GRAP Air Safety Day Planner</span>
          </div>

          {/* Made with AI Tag */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Bot className="w-4 h-4 text-sky-400" />
            <span className="font-medium text-xs">Made with AI</span>
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            <span className="text-[11px] text-slate-400">Aethers AI Engine</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-slate-400">
            © 2026 Saans System. Delhi-NCR Education District Air Safety Framework.
          </div>

          <div className="flex flex-wrap items-center gap-5 text-slate-400">
            <Link href="/conditions" className="hover:text-slate-200 transition-colors flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" />
              <span>Read Conditions</span>
            </Link>
            <Link href="/privacy" className="hover:text-slate-200 transition-colors flex items-center gap-1">
              <Shield className="w-3.5 h-3.5" />
              <span>Privacy Policy</span>
            </Link>
            <Link href="/terms" className="hover:text-slate-200 transition-colors flex items-center gap-1">
              <Scale className="w-3.5 h-3.5" />
              <span>Terms & Conditions</span>
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
