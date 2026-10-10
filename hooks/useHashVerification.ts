import { useState } from 'react';
import { HashChainVerificationResult, AuditBlock } from '@/types/verification';
import { verifyAuditChain } from '@/lib/crypto';
import { INITIAL_AUDIT_CHAIN } from '@/lib/mockData';

export function useHashVerification() {
  const [verification, setVerification] = useState<HashChainVerificationResult | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const verifyChain = async (receiptId: string, customBlocks?: AuditBlock[]) => {
    setIsVerifying(true);
    try {
      const blocksToVerify = customBlocks || INITIAL_AUDIT_CHAIN;
      const result = await verifyAuditChain(blocksToVerify);
      setVerification({
        ...result,
        receiptId
      });
    } catch (err) {
      console.error('Hash chain verification failed:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  return { verifyChain, verification, isVerifying };
}
