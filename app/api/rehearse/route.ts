import { NextRequest, NextResponse } from 'next/server';
import { STAGE_CONFIGS, INITIAL_SCHEDULE } from '@/lib/mockData';
import { GRAPStageNumber } from '@/types/dashboard';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const stageNum: GRAPStageNumber = Number(body.stage) as GRAPStageNumber || 3;

    const stageInfo = STAGE_CONFIGS[stageNum] || STAGE_CONFIGS[3];
    const isBanned = stageNum >= 3;
    const isAdvisory = stageNum === 2;

    const planASchedule = INITIAL_SCHEDULE.map(item => ({
      ...item,
      orderClassification: isBanned && item.isOutdoor ? ('BANNED' as const) : (isAdvisory && item.isOutdoor ? ('ADVISORY' as const) : ('ALLOWED' as const)),
      optimizedAction: item.isOutdoor
        ? (stageNum >= 3
            ? `Plan A: Swapped to ${item.planASwapPeriod || 'P7'} indoor hall | PM2.5 drops to 140 µg/m³`
            : 'Advisory: Shift high cardio to morning slot')
        : 'Regular HEPA classroom'
    }));

    const planBSchedule = INITIAL_SCHEDULE.map(item => ({
      ...item,
      orderClassification: isBanned && item.isOutdoor ? ('BANNED' as const) : ('ALLOWED' as const),
      optimizedAction: item.isOutdoor
        ? `Plan B: Replaced with ${item.planBAlternative || 'Indoor Chess & Wellness'}`
        : 'Regular HEPA classroom'
    }));

    return NextResponse.json({
      stage: stageNum,
      stageInfo,
      peMinutesPreserved: stageNum === 4 ? 90 : 100,
      exposureReductionPct: stageNum === 4 ? 94 : (stageNum === 3 ? 84 : 45),
      affectedClassesCount: stageNum >= 3 ? 4 : (stageNum === 2 ? 2 : 0),
      planASchedule,
      planBSchedule,
      timestamp: new Date().toISOString()
    });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
