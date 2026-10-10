import { RehearsalResponse, ScheduleTodayResponse, NotificationSendResponse } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export const api = {
  async rehearseStage(stage: number): Promise<RehearsalResponse> {
    if (API_BASE) {
      try {
        const res = await fetch(`${API_BASE}/api/simulate-stage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage, preview: true })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn('Backend API unreachable, using client simulation', e);
      }
    }
    
    // Internal API Route
    const res = await fetch('/api/rehearse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage })
    });
    return await res.json();
  },

  async getTodaySchedule(): Promise<ScheduleTodayResponse> {
    const res = await fetch('/api/schedule/today');
    return await res.json();
  },

  async sendNotification(data: { language: 'en' | 'hi'; message: any; recipients: string }): Promise<NotificationSendResponse> {
    const res = await fetch('/api/notifications/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  }
};
