export interface AuditBlock {
  sequence: number;
  hash: string;
  previousHash: string;
  actor: string;
  eventType: string;
  payloadDigest: string;
  timestamp: string;
  isValid?: boolean;
  tampered?: boolean;
}

export interface HashChainVerificationResult {
  receiptId: string;
  isValid: boolean;
  totalBlocks: number;
  blocks: AuditBlock[];
  verifiedAt: string;
  rootHash: string;
  tamperIndex?: number;
}
