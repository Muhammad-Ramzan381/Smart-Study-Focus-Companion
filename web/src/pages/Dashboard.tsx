import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PlusCircle, AlertTriangle, Lightbulb, ArrowRight } from 'lucide-react';
import { api } from '../api';
import { StatCard } from '../components/StatCard';
import { DailyChart, TopicChart } from '../components/Charts';
import { SessionCard } from '../components/SessionCard';
import type { WeeklyReport, Session } from '../types';

export function Dashboard() {
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [reportData, sessionsData] = await Promise.all([
          api.getWeeklyReport(),
          api.getSessions(),
        ]);
        setReport(reportData);
        setSessions(sessionsData.slice(-5).reverse());
      } catch (err) {
        setError('Failed to load dashboard data. Is the API server running?');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-white/60">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <div className="text-red-400 mb-4">{error}</div>
        <p className="text-white/60 text-sm">
          Make sure the API server is running: <code className="bg-white/10 px-2 py-1 rounded">python api/main.py</code>
        </p>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Weekly Overview</h1>
          <p className="text-white/60 mt-1">
            {report.period.start} to {report.period.end}
          </p>
        </div>
        <Link
          to="/session/new"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold transition"
        >
          <PlusCircle className="w-5 h-5" />
          Start Session
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Study Time"
          value={`${Math.round(report.overview.this_week.time)} min`}
          change={report.overview.time_change}
          changeLabel="min vs last week"
        />
        <StatCard
          label="Sessions"
          value={report.overview.this_week.sessions}
          change={report.overview.sessions_change}
          changeLabel="vs last week"
        />
        <StatCard
          label="Avg Relevance"
          value={`${Math.round(report.overview.this_week.avg_relevance)}%`}
          changeLabel="topic alignment"
        />
        <StatCard
          label="Issues Detected"
          value={report.overview.this_week.issues}
          changeLabel="drift & overconfidence"
          highlight={report.overview.this_week.issues > 0}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">Daily Study Time</h3>
          <DailyChart data={report.daily_breakdown} />
        </div>
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">Topics This Week</h3>
          <TopicChart data={report.topic_analysis} />
        </div>
      </div>

      {/* Problem Areas */}
      {report.problem_areas.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            Areas Needing Attention
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {report.problem_areas.map((problem, i) => (
              <div
                key={i}
                className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4"
              >
                <div className="font-semibold">{problem.topic}</div>
                <div className="text-sm text-white/60 mt-1">
                  {problem.sessions} sessions
                </div>
                <ul className="text-sm mt-2 space-y-1">
                  {problem.issues.map((issue, j) => (
                    <li key={j} className="text-yellow-300">
                      • {issue}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Sessions */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Sessions</h3>
          <Link
            to="/history"
            className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
          >
            View all <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {sessions.length > 0 ? (
          <div className="space-y-3">
            {sessions.map(session => (
              <SessionCard key={session.id} session={session} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-white/50">
            <div className="text-4xl mb-2">📚</div>
            <p>No sessions yet. Start your first study session!</p>
          </div>
        )}
      </div>

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-blue-400" />
            Recommendations
          </h3>
          <ul className="space-y-2">
            {report.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2">
                <ArrowRight className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
