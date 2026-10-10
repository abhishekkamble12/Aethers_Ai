import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getAQIColor(aqi: number): string {
  if (aqi <= 100) return 'text-green-400';
  if (aqi <= 200) return 'text-yellow-400';
  if (aqi <= 300) return 'text-orange-400';
  if (aqi <= 400) return 'text-red-400';
  return 'text-purple-400';
}

export function getAQIBg(aqi: number): string {
  if (aqi <= 100) return 'bg-green-500/20 text-green-300 border-green-500/30';
  if (aqi <= 200) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
  if (aqi <= 300) return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
  if (aqi <= 400) return 'bg-red-500/20 text-red-300 border-red-500/30';
  return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
}

export function getStageColor(stage: number): string {
  switch (stage) {
    case 1: return 'badge-stage-1';
    case 2: return 'badge-stage-2';
    case 3: return 'badge-stage-3';
    case 4: return 'badge-stage-4';
    default: return 'bg-gray-500/20 text-gray-300';
  }
}
