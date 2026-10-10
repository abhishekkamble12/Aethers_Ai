import { create } from 'zustand';
import { GRAPStageNumber, TimetableEntry } from '@/types/dashboard';
import { AuditBlock } from '@/types/verification';
import { INITIAL_SCHEDULE, INITIAL_AUDIT_CHAIN } from '@/lib/mockData';

interface DashboardStore {
  currentStage: GRAPStageNumber;
  selectedPlan: 'A' | 'B' | null;
  schedule: TimetableEntry[];
  auditChain: AuditBlock[];
  isApproved: boolean;
  approvedPlan: 'A' | 'B' | null;
  
  setStage: (stage: GRAPStageNumber) => void;
  setSelectedPlan: (plan: 'A' | 'B' | null) => void;
  setSchedule: (schedule: TimetableEntry[]) => void;
  approvePlan: (plan: 'A' | 'B') => void;
  setAuditChain: (chain: AuditBlock[]) => void;
  tamperAuditBlock: (index: number) => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  currentStage: 3,
  selectedPlan: 'B',
  schedule: INITIAL_SCHEDULE,
  auditChain: INITIAL_AUDIT_CHAIN,
  isApproved: false,
  approvedPlan: null,

  setStage: (stage) => set({ currentStage: stage }),
  setSelectedPlan: (plan) => set({ selectedPlan: plan }),
  setSchedule: (schedule) => set({ schedule }),
  approvePlan: (plan) => set((state) => {
    const newSeq = state.auditChain.length + 1;
    const prevHash = state.auditChain[state.auditChain.length - 1]?.hash || '0000000000000000000000000000000000000000000000000000000000000000';
    const newBlock: AuditBlock = {
      sequence: newSeq,
      previousHash: prevHash,
      actor: 'principal:sch_481_delhi',
      eventType: `PRINCIPAL_APPROVED_PLAN_${plan}`,
      payloadDigest: Math.random().toString(36).substring(2) + Math.random().toString(36).substring(2),
      timestamp: new Date().toISOString(),
      hash: Math.random().toString(16).substring(2) + Math.random().toString(16).substring(2) + Math.random().toString(16).substring(2),
      isValid: true
    };
    return {
      isApproved: true,
      approvedPlan: plan,
      selectedPlan: plan,
      auditChain: [...state.auditChain, newBlock]
    };
  }),
  setAuditChain: (chain) => set({ auditChain: chain }),
  tamperAuditBlock: (index) => set((state) => {
    const newChain = [...state.auditChain];
    if (newChain[index]) {
      newChain[index] = {
        ...newChain[index],
        payloadDigest: 'CORRUPTED_PAYLOAD_DIGEST_X999',
        tampered: true,
        isValid: false
      };
    }
    return { auditChain: newChain };
  })
}));
