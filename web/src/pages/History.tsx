import { useEffect, useState } from 'react';
import { api } from '../api';
import { SessionCard } from '../components/SessionCard';
import type { Session } from '../types';
import { History as HistoryIcon, Calendar, Clock, Target } from 'lucide-react';

export function History() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSessions() {
      try {
        const data = await api.getSessions();
        setSessions(data.reverse()); // Most recent first
      } catch (error) {
        console.error('Failed to fetch sessions:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchSessions();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-white/60">Loading history...</div>
      </div>
    );
  }

  // Group sessions by date
  const groupedSessions = sessions.reduce((acc, session) => {
    const date = session.start_time.slice(0, 10);
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(session);
    return acc;
  }, {} as Record<string, Session[]>);

  const totalMinutes = sessions.reduce((sum, s) => sum + s.actual_minutes, 0);
  const avgRelevance = sessions.length
    ? sessions.reduce((sum, s) => sum + s.topic_relevance_score, 0) / sessions.length
    : 0;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <HistoryIcon className="w-8 h-8 text-blue-400" />
            Session History
          </h1>
          <p className="text-white/60 mt-1">
            {sessions.length} total sessions
          </p>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4 flex items-center gap-4">
          <div className="bg-blue-500/20 p-3 rounded-lg">
            <Clock className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <div className="text-2xl font-bold">
              {Math.round(totalMinutes / 60 * 10) / 10}h
            </div>
            <div className="text-white/60 text-sm">Total study time</div>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-4">
          <div className="bg-green-500/20 p-3 rounded-lg">
            <Target className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <div className="text-2xl font-bold">{Math.round(avgRelevance)}%</div>
            <div className="text-white/60 text-sm">Average relevance</div>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-4">
          <div className="bg-purple-500/20 p-3 rounded-lg">
            <Calendar className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <div className="text-2xl font-bold">{Object.keys(groupedSessions).length}</div>
            <div className="text-white/60 text-sm">Days studied</div>
          </div>
        </div>
      </div>

      {/* Sessions by Date */}
      {sessions.length > 0 ? (
        <div className="space-y-6">
          {Object.entries(groupedSessions).map(([date, dateSessions]) => (
            <div key={date}>
              <div className="flex items-center gap-2 mb-3">
                <Calendar className="w-4 h-4 text-white/40" />
                <h2 className="text-white/60 font-medium">
                  {new Date(date).toLocaleDateString('en-US', {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                  })}
                </h2>
                <span className="text-white/40 text-sm">
                  • {dateSessions.length} session{dateSessions.length > 1 ? 's' : ''}
                </span>
              </div>
              <div className="space-y-3">
                {dateSessions.map(session => (
                  <SessionCard key={session.id} session={session} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-4">📚</div>
          <h3 className="text-xl font-semibold mb-2">No sessions yet</h3>
          <p className="text-white/60">
            Complete your first study session to see your history here.
          </p>
        </div>
      )}
    </div>
  );
}
