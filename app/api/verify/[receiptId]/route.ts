import { NextRequest, NextResponse } from 'next/server';
import { INITIAL_AUDIT_CHAIN } from '@/lib/mockData';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ receiptId: string }> }
) {
  const { receiptId } = await params;

  return NextResponse.json({
    receiptId: receiptId || 'receipt-001',
    schoolId: 'SCH_481_DELHI',
    schoolName: 'Delhi Public Air-Safety Academy, Sector 4',
    auditHead: INITIAL_AUDIT_CHAIN[INITIAL_AUDIT_CHAIN.length - 1].hash,
    blocks: INITIAL_AUDIT_CHAIN,
    verifiedAt: new Date().toISOString()
  });
}
