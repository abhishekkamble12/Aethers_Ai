'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, RefreshCw, Lock } from 'lucide-react';
import { useDashboardStore } from '@/store/dashboardStore';
import { useHashVerification } from '@/hooks/useHashVerification';

export function HashChainVerifier({ receiptId = 'receipt-001' }: { receiptId?: string }) {
  const { auditChain, tamperAuditBlock } = useDashboardStore();
  const { verifyChain, verification, isVerifying } = useHashVerification();

  useEffect(() => {
    verifyChain(receiptId, auditChain);
  }, [receiptId, auditChain]);

  const handleTamperSim = (index: number) => {
    tamperAuditBlock(index);
  };

  return (
    <div className="glass-card p-6 border-slate-800 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-slate-800 text-slate-300">
              <Lock className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Cryptographic Hash Chain Verifier
            </h2>
          </div>
          <p className="text-slate-300 text-xs">
            WebCrypto SHA-256 tamper-evident proof ledger for GRAP schedule compliance
          </p>
        </div>

        <button
          onClick={() => verifyChain(receiptId, auditChain)}
          disabled={isVerifying}
          className="btn-primary text-xs py-2 px-3"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
          <span>{isVerifying ? 'Recomputing SHA-256...' : 'Re-verify Chain'}</span>
        </button>
      </div>

      {/* Verification Status Banner */}
      {verification && (
        <div className={`p-4 rounded-lg border flex items-start gap-3.5 ${
          verification.isValid
            ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
            : 'bg-rose-950/40 border-rose-500/50 text-rose-200'
        }`}>
          {verification.isValid ? (
            <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
          )}

          <div className="flex-1">
            <div className="flex items-center justify-between font-bold text-sm text-white">
              <span>
                Audit Chain Status: {verification.isValid ? 'VALID UNTAMPERED' : 'CHAIN BROKEN TAMPER DETECTED'}
              </span>
              <span className="text-[11px] font-mono font-normal px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                {verification.totalBlocks} Blocks Verified
              </span>
            </div>
            <p className="text-xs mt-1 text-slate-300">
              {verification.isValid
                ? 'All block hashes, canonical JSON payloads, and SHA-256 parent linkages match original EventBridge digest.'
                : `Corrupted payload digest detected at Block #${(verification.tamperIndex ?? 0) + 1}. Cryptographic integrity broken.`}
            </p>
          </div>
        </div>
      )}

      {/* Block Chain Display */}
      <div className="space-y-3">
        {auditChain.map((block, index) => (
          <div
            key={block.sequence}
            className={`p-4 rounded-lg border transition-colors ${
              block.isValid !== false
                ? 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                : 'bg-rose-950/30 border-rose-500/50'
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                  Block #{block.sequence.toString().padStart(4, '0')}
                </span>
                <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                  {block.eventType}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className={`text-[11px] font-bold font-mono px-2 py-0.5 rounded ${
                  block.isValid !== false ? 'bg-emerald-500/10 text-emerald-300' : 'bg-rose-500/10 text-rose-300'
                }`}>
                  {block.isValid !== false ? 'VALID' : 'TAMPERED'}
                </span>

                <button
                  onClick={() => handleTamperSim(index)}
                  className="text-[11px] px-2 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition-colors"
                >
                  Simulate Tamper
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs mb-2">
              <div>
                <span className="text-slate-400">Actor Role: </span>
                <span className="font-mono text-slate-200 font-semibold">{block.actor}</span>
              </div>
              <div>
                <span className="text-slate-400">Timestamp: </span>
                <span className="font-mono text-slate-200">{new Date(block.timestamp).toLocaleString()}</span>
              </div>
            </div>

            <div className="space-y-0.5 text-[11px] font-mono">
              <div className="flex flex-col sm:flex-row sm:items-center gap-1">
                <span className="text-slate-500 w-20">Prev Hash:</span>
                <span className="text-slate-400 truncate">{block.previousHash}</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1">
                <span className="text-blue-400 w-20">Block Hash:</span>
                <span className="text-blue-300 font-semibold truncate">{block.hash}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
