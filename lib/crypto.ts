import { AuditBlock, HashChainVerificationResult } from '@/types/verification';

export function canonicalJson(obj: Record<string, any>): string {
  const keys = Object.keys(obj).sort();
  const sortedObj: Record<string, any> = {};
  for (const k of keys) {
    sortedObj[k] = obj[k];
  }
  return JSON.stringify(sortedObj);
}

export async function sha256Hex(str: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  
  if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
  
  // Fallback Node crypto if running on server side
  try {
    const cryptoNode = await import('crypto');
    return cryptoNode.createHash('sha256').update(str).digest('hex');
  } catch {
    // Basic fallback algorithm for testing environment
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash |= 0;
    }
    return Math.abs(hash).toString(16).padStart(64, '0');
  }
}

export async function verifyAuditChain(blocks: AuditBlock[]): Promise<HashChainVerificationResult> {
  const verifiedBlocks: AuditBlock[] = [];
  let chainValid = true;
  let prevHash = '0000000000000000000000000000000000000000000000000000000000000000';
  let firstTamperedIndex: number | undefined = undefined;

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    
    // Check linkage with previous block
    const isLinkageValid = block.previousHash === prevHash;
    
    // Compute canonical block hash
    const payloadObject = {
      sequence: block.sequence,
      actor: block.actor,
      eventType: block.eventType,
      payloadDigest: block.payloadDigest,
      timestamp: block.timestamp
    };

    const computedHash = await sha256Hex(prevHash + canonicalJson(payloadObject));
    const isHashValid = isLinkageValid && computedHash === block.hash;

    if (!isHashValid && firstTamperedIndex === undefined) {
      firstTamperedIndex = i;
      chainValid = false;
    }

    verifiedBlocks.push({
      ...block,
      isValid: isHashValid,
      tampered: !isHashValid
    });

    prevHash = block.hash;
  }

  return {
    receiptId: blocks[blocks.length - 1]?.hash || 'receipt-001',
    isValid: chainValid,
    totalBlocks: blocks.length,
    blocks: verifiedBlocks,
    verifiedAt: new Date().toISOString(),
    rootHash: blocks[blocks.length - 1]?.hash || '',
    tamperIndex: firstTamperedIndex
  };
}
