import { create } from 'zustand';

export interface SentNotification {
  id: string;
  language: 'en' | 'hi';
  title: string;
  status: 'SENT' | 'DELIVERED';
  recipientCount: number;
  timestamp: string;
}

interface NotificationStore {
  history: SentNotification[];
  addNotification: (item: Omit<SentNotification, 'id' | 'timestamp'>) => void;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  history: [
    {
      id: 'notif-1',
      language: 'en',
      title: 'GRAP Stage III Outdoor Suspension Notice',
      status: 'DELIVERED',
      recipientCount: 1420,
      timestamp: '09:00:00 AM'
    },
    {
      id: 'notif-2',
      language: 'hi',
      title: 'समय सारणी अपडेट - इनडोर सत्र',
      status: 'DELIVERED',
      recipientCount: 1420,
      timestamp: '08:00:00 AM'
    }
  ],
  addNotification: (item) => set((state) => ({
    history: [
      {
        ...item,
        id: `notif-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString()
      },
      ...state.history
    ]
  }))
}));
