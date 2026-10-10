import { GRAPStageInfo, TimetableEntry } from '@/types/dashboard';
import { AuditBlock } from '@/types/verification';

export const STAGE_CONFIGS: Record<number, GRAPStageInfo> = {
  1: {
    stage: 1,
    name: 'Stage I',
    stageCode: 'I',
    aqiRange: '201-300 (Poor)',
    outdoorAllowed: true,
    orderCode: 'r-012',
    reason: 'Stage I Directive: Standard activity with advisory for sensitive groups. Air filters active in indoor classrooms.',
    color: 'yellow'
  },
  2: {
    stage: 2,
    name: 'Stage II',
    stageCode: 'II',
    aqiRange: '301-400 (Very Poor)',
    outdoorAllowed: false,
    orderCode: 'r-015',
    reason: 'Stage II Advisory: Reschedule high-exposure outdoor sports into cleaner morning/evening slots.',
    color: 'orange'
  },
  3: {
    stage: 3,
    name: 'Stage III',
    stageCode: 'III',
    aqiRange: '401-450 (Severe)',
    outdoorAllowed: false,
    orderCode: 'r-017',
    reason: 'Stage III Directive (r-017): All outdoor sports and PT strictly suspended. Plan B indoor wellness active.',
    color: 'red'
  },
  4: {
    stage: 4,
    name: 'Stage IV',
    stageCode: 'IV',
    aqiRange: '>450 (Severe+)',
    outdoorAllowed: false,
    orderCode: 'r-020',
    reason: 'Stage IV Emergency: Absolute outdoor ban. Primary classes moved online, high-school indoor hybrid protocol active.',
    color: 'purple'
  }
};

export const INITIAL_SCHEDULE: TimetableEntry[] = [
  {
    id: 'sched-1',
    class: '7A',
    period: 'P2',
    time: '09:10 - 09:50',
    originalActivity: 'PT & Athletics (Ground A)',
    subject: 'Physical Education',
    teacher: 'Mr. Vikram Singh (PE)',
    isOutdoor: true,
    forecastPM25: 395,
    orderClassification: 'BANNED',
    optimizedAction: 'Plan A: Swapped to P7 (13:20 PM) | PM2.5 forecast drops to 140 µg/m³',
    venue: 'Indoor Gym 1',
    planASwapPeriod: 'P7',
    planBAlternative: 'Indoor Yoga & Breathing Exercises'
  },
  {
    id: 'sched-2',
    class: '7B',
    period: 'P2',
    time: '09:10 - 09:50',
    originalActivity: 'Football Practice (Ground B)',
    subject: 'Physical Education',
    teacher: 'Ms. Ananya Sharma (PE)',
    isOutdoor: true,
    forecastPM25: 395,
    orderClassification: 'BANNED',
    optimizedAction: 'Plan B: Replaced with Indoor Table Tennis & Mind Sports',
    venue: 'Multipurpose Indoor Hall',
    planASwapPeriod: 'P8',
    planBAlternative: 'Indoor Chess & Reflex Drills'
  },
  {
    id: 'sched-3',
    class: '8A',
    period: 'P4',
    time: '10:45 - 11:25',
    originalActivity: 'Basketball Training',
    subject: 'Physical Education',
    teacher: 'Mr. Vikram Singh (PE)',
    isOutdoor: true,
    forecastPM25: 410,
    orderClassification: 'BANNED',
    optimizedAction: 'Plan B: Shifted to Air-Filtered Badminton Court',
    venue: 'Indoor Sports Complex B',
    planASwapPeriod: 'P7',
    planBAlternative: 'Indoor Badminton Session'
  },
  {
    id: 'sched-4',
    class: '9A',
    period: 'P5',
    time: '12:00 - 12:40',
    originalActivity: 'Cricket Conditioning',
    subject: 'Sports & Conditioning',
    teacher: 'Ms. Ananya Sharma (PE)',
    isOutdoor: true,
    forecastPM25: 350,
    orderClassification: 'BANNED',
    optimizedAction: 'Plan A: Swapped with P8 Library Research Period',
    venue: 'Central Library Hall B',
    planASwapPeriod: 'P8',
    planBAlternative: 'Indoor Ergometrics & Fitness Analytics'
  },
  {
    id: 'sched-5',
    class: '6A',
    period: 'P1',
    time: '08:30 - 09:10',
    originalActivity: 'English Literature',
    subject: 'English',
    teacher: 'Dr. Rajesh Verma',
    isOutdoor: false,
    forecastPM25: 210,
    orderClassification: 'ALLOWED',
    optimizedAction: 'Regular Class (HEPA Filter Active)',
    venue: 'Classroom 6A (Block 2)'
  },
  {
    id: 'sched-6',
    class: '10A',
    period: 'P3',
    time: '10:05 - 10:45',
    originalActivity: 'Physics Practical Lab',
    subject: 'Physics',
    teacher: 'Mrs. Sunita Kapoor',
    isOutdoor: false,
    forecastPM25: 360,
    orderClassification: 'ALLOWED',
    optimizedAction: 'Regular Lab Session (Monitored Air Quality)',
    venue: 'Physics Lab 2'
  }
];

export const INITIAL_AUDIT_CHAIN: AuditBlock[] = [
  {
    sequence: 1,
    previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
    actor: 'scheduler:eventbridge',
    eventType: 'STAGE_III_FORECAST_INGESTED',
    payloadDigest: '9f83a48e89f89a9f4b11f010f3c5ec7b3e15b630325f190e227fc69e2c608034',
    timestamp: '2026-10-10T05:30:00.000Z',
    hash: '3b9a7852c08ea3cfdfa4421b4a3a60dbbcf3a1e9c8bc8c78c801e8a93e3518e1',
    isValid: true
  },
  {
    sequence: 2,
    previousHash: '3b9a7852c08ea3cfdfa4421b4a3a60dbbcf3a1e9c8bc8c78c801e8a93e3518e1',
    actor: 'rules_engine:grap_v2',
    eventType: 'RULES_EVALUATED_RULESET_R017',
    payloadDigest: '148e6589324adfe95c026d302b1154c185bbbc228c89b77d612e3ef2479e3940',
    timestamp: '2026-10-10T05:30:02.000Z',
    hash: '61ea150c22fa15e5c709e8b61c94d1a3c7cba2a32c4bbf3b0928929949603e5c',
    isValid: true
  },
  {
    sequence: 3,
    previousHash: '61ea150c22fa15e5c709e8b61c94d1a3c7cba2a32c4bbf3b0928929949603e5c',
    actor: 'planner:deterministic_v1',
    eventType: 'PLAN_A_B_GENERATED',
    payloadDigest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    timestamp: '2026-10-10T05:30:05.000Z',
    hash: '9312dc86c8f2ba57147e4ad3d9c72d9b6d9a32c3f81eb5ba1a6bf9a09995c0c2',
    isValid: true
  },
  {
    sequence: 4,
    previousHash: '9312dc86c8f2ba57147e4ad3d9c72d9b6d9a32c3f81eb5ba1a6bf9a09995c0c2',
    actor: 'principal:sch_481_delhi',
    eventType: 'PRINCIPAL_APPROVED_PLAN_B',
    payloadDigest: '7c81d904e223fa87110bc8d91a92a10d9f43058b1009121a8112c3f56d9014b2',
    timestamp: '2026-10-10T06:15:22.000Z',
    hash: '1a82f9c4d81720a455bb2a09124f114c990a12e3456789abc0123456789abcdef',
    isValid: true
  }
];

export const HOURLY_AQI_TREND = [
  { time: '06:00', aqi: 310, pm25: 220, stage: 2 },
  { time: '08:00', aqi: 395, pm25: 290, stage: 2 },
  { time: '10:00', aqi: 425, pm25: 340, stage: 3 },
  { time: '12:00', aqi: 442, pm25: 385, stage: 3 },
  { time: '14:00', aqi: 415, pm25: 330, stage: 3 },
  { time: '16:00', aqi: 380, pm25: 280, stage: 2 },
  { time: '18:00', aqi: 340, pm25: 240, stage: 2 },
  { time: '20:00', aqi: 290, pm25: 195, stage: 1 }
];

export const DELHI_ZONES = [
  { id: 'zone-1', name: 'Central Delhi (Pusa Rd)', aqi: 412, stage: 3, schoolsCount: 42, compliancePct: 100 },
  { id: 'zone-2', name: 'South Delhi (R.K. Puram)', aqi: 448, stage: 3, schoolsCount: 68, compliancePct: 100 },
  { id: 'zone-3', name: 'North Delhi (DU North)', aqi: 462, stage: 4, schoolsCount: 39, compliancePct: 97.4 },
  { id: 'zone-4', name: 'East Delhi (Anand Vihar)', aqi: 485, stage: 4, schoolsCount: 54, compliancePct: 98.1 },
  { id: 'zone-5', name: 'Noida Sector 62', aqi: 385, stage: 2, schoolsCount: 47, compliancePct: 100 },
  { id: 'zone-6', name: 'Gurugram Cyber City', aqi: 360, stage: 2, schoolsCount: 51, compliancePct: 100 }
];
