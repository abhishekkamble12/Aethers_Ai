'use client';

import { ShieldCheck, QrCode } from 'lucide-react';

export function ReceiptDisplay({ receiptId = 'receipt-delhi-sch-481' }: { receiptId?: string }) {
  const rootHash = '1a82f9c4d81720a455bb2a09124f114c990a12e3456789abc0123456789abcdef';

  return (
    <div className="glass-card p-6 border-slate-800 space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-base text-white">Cryptographic Compliance Receipt</h3>
            <p className="text-xs text-slate-400 font-mono">Receipt ID: {receiptId}</p>
          </div>
        </div>

        <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-mono">
          VERIFIED & SEALED
        </span>
      </div>

      <div className="space-y-4 text-xs">
        <div className="grid grid-cols-2 gap-3 p-3.5 rounded-lg bg-slate-900 border border-slate-800">
          <div>
            <div className="text-slate-400">School Establishment</div>
            <div className="font-semibold text-white mt-0.5">Delhi Public Air-Safety Academy</div>
            <div className="text-slate-400 mt-0.5">School ID: SCH_481_DELHI</div>
          </div>
          <div>
            <div className="text-slate-400">GRAP Directive Executed</div>
            <div className="font-semibold text-amber-300 mt-0.5">Stage III Order (r-017)</div>
            <div className="text-slate-400 mt-0.5">AQI Range: 401-450 Severe</div>
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="font-semibold text-slate-400 uppercase tracking-wider text-[11px]">Root SHA-256 State Digest</div>
          <div className="p-3 rounded bg-slate-950 font-mono text-xs text-teal-300 break-all border border-slate-800">
            {rootHash}
          </div>
        </div>

        <div className="flex items-center justify-between p-3.5 rounded-lg bg-slate-900 border border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded bg-white text-slate-900">
              <QrCode className="w-6 h-6" />
            </div>
            <div>
              <div className="font-bold text-white">Public Verification Endpoint</div>
              <div className="text-blue-400 font-mono text-[11px] mt-0.5">https://saans.delhi.gov.in/verify/{receiptId}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
