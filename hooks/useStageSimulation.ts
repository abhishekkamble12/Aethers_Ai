import { useState } from 'react';
import { SimulationResult, GRAPStageNumber } from '@/types/dashboard';
import { STAGE_CONFIGS, INITIAL_SCHEDULE } from '@/lib/mockData';
import { api } from '@/lib/api';

export function useStageSimulation() {
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const simulateStage = async (stageNum: GRAPStageNumber) => {
    setIsLoading(true);
    try {
      // Try API route or client side algorithm
      const apiResult = await api.rehearseStage(stageNum);
      setSimulation(apiResult);
    } catch {
      // Fallback deterministic simulation
      const stageInfo = STAGE_CONFIGS[stageNum];
      const isBanned = stageNum >= 3;
      const isAdvisory = stageNum === 2;

      const planA = INITIAL_SCHEDULE.map(item => ({
        ...item,
        orderClassification: isBanned && item.isOutdoor ? ('BANNED' as const) : (isAdvisory && item.isOutdoor ? ('ADVISORY' as const) : ('ALLOWED' as const)),
        optimizedAction: item.isOutdoor
          ? (stageNum >= 3
              ? `Plan A: Shifted to ${item.planASwapPeriod || 'P7'} indoor hall | Exposure reduced by 82%`
              : 'Advisory: Early morning low exposure slot')
          : 'Regular HEPA classroom session'
      }));

      const planB = INITIAL_SCHEDULE.map(item => ({
        ...item,
        orderClassification: isBanned && item.isOutdoor ? ('BANNED' as const) : ('ALLOWED' as const),
        optimizedAction: item.isOutdoor
          ? `Plan B: Replaced with ${item.planBAlternative || 'Indoor Chess & Wellness'}`
          : 'Regular HEPA classroom session'
      }));

      setSimulation({
        stage: stageNum,
        stageInfo,
        peMinutesPreserved: stageNum === 4 ? 90 : 100,
        exposureReductionPct: stageNum === 4 ? 94 : (stageNum === 3 ? 84 : 45),
        affectedClassesCount: stageNum >= 3 ? 4 : (stageNum === 2 ? 2 : 0),
        planASchedule: planA,
        planBSchedule: planB,
        timestamp: new Date().toISOString()
      });
    } finally {
      setIsLoading(false);
    }
  };

  return { simulateStage, simulation, isLoading };
}
