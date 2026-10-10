import { Suspense } from 'react';
import { ReceiptDisplay } from '@/components/verification/ReceiptDisplay';
import { HashChainVerifier } from '@/components/verification/HashChainVerifier';

async function ReceiptView({ params }: { params: Promise<{ receiptId: string }> }) {
  const { receiptId } = await params;

  return (
    <>
      <ReceiptDisplay receiptId={receiptId} />
      <HashChainVerifier receiptId={receiptId} />
    </>
  );
}

export default function SpecificReceiptPage(props: { params: Promise<{ receiptId: string }> }) {
  return (
    <div className="container mx-auto px-4 md:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-white tracking-tight">
          📜 Audit Proof Receipt Verification
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Verifiable cryptographic proof receipt issued to Delhi Public Air-Safety Academy
        </p>
      </div>

      <Suspense fallback={<div className="glass-card p-12 text-center text-slate-400 animate-pulse">Loading receipt cryptographic proof...</div>}>
        <ReceiptView params={props.params} />
      </Suspense>
    </div>
  );
}
