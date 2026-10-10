import { NextResponse } from 'next/server';
import { INITIAL_SCHEDULE, INITIAL_AUDIT_CHAIN } from '@/lib/mockData';

export async function GET() {
  const rootHash = INITIAL_AUDIT_CHAIN[INITIAL_AUDIT_CHAIN.length - 1].hash;

  return NextResponse.json({
    peMinutesPreserved: 100,
    exposureAvoidedPct: 84.5,
    auditHead: rootHash.substring(0, 16) + '...',
    schedule: INITIAL_SCHEDULE,
    currentStage: 3,
    currentAQI: 415,
    currentPM25: 340
  });
}
