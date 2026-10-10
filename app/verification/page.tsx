'use client';

import { HashChainVerifier } from '@/components/verification/HashChainVerifier';
import { ReceiptDisplay } from '@/components/verification/ReceiptDisplay';

export default function VerificationPage() {
  return (
    <div className="container mx-auto px-4 md:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Cryptographic Public Verification Ledger
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          WebCrypto SHA-256 hash chain verification portal for public audits & regulatory compliance
        </p>
      </div>

      <ReceiptDisplay receiptId="receipt-delhi-sch-481" />
      <HashChainVerifier receiptId="receipt-delhi-sch-481" />
    </div>
  );
}
