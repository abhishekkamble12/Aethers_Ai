import { SimulationResult, TimetableEntry } from './dashboard';
import { AuditBlock, HashChainVerificationResult } from './verification';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface RehearsalRequest {
  stage: number;
  preview?: boolean;
}

export interface RehearsalResponse extends SimulationResult {}

export interface ScheduleTodayResponse {
  peMinutesPreserved: number;
  exposureAvoidedPct: number;
  auditHead: string;
  schedule: TimetableEntry[];
  currentStage: number;
  currentAQI: number;
  currentPM25: number;
}

export interface NotificationSendRequest {
  language: 'en' | 'hi';
  message: {
    title: string;
    body: string;
    ack: string;
  };
  recipients: string;
}

export interface NotificationSendResponse {
  sentId: string;
  status: 'SENT' | 'FAILED';
  recipientCount: number;
  timestamp: string;
}
