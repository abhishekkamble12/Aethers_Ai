import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { language, recipients } = body;

    return NextResponse.json({
      sentId: `MSG-${Date.now()}`,
      status: 'SENT',
      recipientCount: recipients === 'all_parents' ? 1420 : 1,
      language: language || 'en',
      timestamp: new Date().toISOString()
    });
  } catch {
    return NextResponse.json({ error: 'Failed to process notification request' }, { status: 400 });
  }
}
