// API client for Study Companion

import type { Session, WeeklyReport, Stats, SessionFormData } from './types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  // Sessions
  getSessions: () => fetchJSON<Session[]>('/sessions'),

  getSession: (id: string) => fetchJSON<Session>(`/sessions/${id}`),

  createSession: (data: SessionFormData) =>
    fetchJSON<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Reports
  getWeeklyReport: () => fetchJSON<WeeklyReport>('/report'),

  // Stats
  getStats: () => fetchJSON<Stats>('/stats'),

  // Health check
  healthCheck: () => fetchJSON<{ status: string }>('/health'),
};
