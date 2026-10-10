import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    service: 'saans-frontend-nextjs',
    grapEngine: 'active',
    webCrypto: 'supported',
    timestamp: new Date().toISOString()
  });
}
