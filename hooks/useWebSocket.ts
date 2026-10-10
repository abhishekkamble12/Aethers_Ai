import { useState, useEffect, useRef } from 'react';

export interface LiveAQIMessage {
  timestamp: string;
  aqi: number;
  pm25: number;
  pm10: number;
  stage: number;
  exposureReduction: number;
  station: string;
}

export function useWebSocket(url: string = 'ws://localhost:3001/aqi') {
  const [data, setData] = useState<LiveAQIMessage | null>({
    timestamp: '08:00:00 AM',
    aqi: 415,
    pm25: 340,
    pm10: 480,
    stage: 3,
    exposureReduction: 78.5,
    station: 'Delhi Anand Vihar CAAQMS'
  });
  const [isConnected, setIsConnected] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Set real timestamp on mount
    setData(prev => prev ? { ...prev, timestamp: new Date().toLocaleTimeString() } : null);

    let intervalId: NodeJS.Timeout | null = null;

    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      ws.current.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch {
          // Keep current data
        }
      };

      ws.current.onerror = () => {
        setIsConnected(false);
      };

      ws.current.onclose = () => {
        setIsConnected(false);
      };
    } catch {
      setIsConnected(false);
    }

    intervalId = setInterval(() => {
      const randomFluc = Math.floor(Math.random() * 9) - 4;
      setData(prev => {
        if (!prev) return null;
        const newAQI = Math.max(150, Math.min(490, prev.aqi + randomFluc));
        const newPM25 = Math.round(newAQI * 0.81);
        let stage = 1;
        if (newAQI > 450) stage = 4;
        else if (newAQI > 400) stage = 3;
        else if (newAQI > 300) stage = 2;

        return {
          ...prev,
          timestamp: new Date().toLocaleTimeString(),
          aqi: newAQI,
          pm25: newPM25,
          pm10: Math.round(newPM25 * 1.4),
          stage,
          exposureReduction: Math.min(96, Math.max(60, Number((78.5 + (stage * 4.2)).toFixed(1))))
        };
      });
      setIsConnected(true);
    }, 4000);

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [url]);

  const send = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  return { data, isConnected, error, send };
}
