export type GRAPStageNumber = 1 | 2 | 3 | 4;

export interface GRAPStageInfo {
  stage: GRAPStageNumber;
  name: string;
  stageCode: string;
  aqiRange: string;
  outdoorAllowed: boolean;
  orderCode: string;
  reason: string;
  color: string;
}

export interface TimetableEntry {
  id: string;
  class: string;
  period: string;
  time: string;
  originalActivity: string;
  subject: string;
  teacher: string;
  isOutdoor: boolean;
  forecastPM25: number;
  orderClassification: 'BANNED' | 'ADVISORY' | 'ALLOWED';
  optimizedAction: string;
  venue?: string;
  planASwapPeriod?: string;
  planBAlternative?: string;
}

export interface KPIMetrics {
  peMinutesPreserved: number;
  exposureAvoidedPct: number;
  currentStage: GRAPStageNumber;
  currentAQI: number;
  currentPM25: number;
  auditHead: string;
  totalClassesRescheduled: number;
}

export interface SimulationResult {
  stage: GRAPStageNumber;
  stageInfo: GRAPStageInfo;
  peMinutesPreserved: number;
  exposureReductionPct: number;
  affectedClassesCount: number;
  planASchedule: TimetableEntry[];
  planBSchedule: TimetableEntry[];
  timestamp: string;
}
