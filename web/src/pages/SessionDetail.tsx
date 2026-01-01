import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Target,
  AlertTriangle,
  CheckCircle,
  Coffee,
  FileText,
  Lightbulb,
  Calendar,
} from 'lucide-react';
import { api } from '../api';
import type { Session } from '../types';

export function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSession() {
      if (!id) return;
      try {
        const data = await api.getSession(id);
        setSession(data);
      } catch (error) {
        console.error('Failed to fetch session:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchSession();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-white/60">Loading session...</div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">🔍</div>
        <h2 className="text-xl font-semibold mb-2">Session not found</h2>
        <Link to="/history" className="text-blue-400 hover:text-blue-300">
          ← Back to history
        </Link>
      </div>
    );
  }

  const relevanceColor =
    session.topic_relevance_score >= 70
      ? 'text-green-400'
      : session.topic_relevance_score >= 50
      ? 'text-yellow-400'
      : 'text-red-400';

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/history"
          className="inline-flex items-center gap-1 text-white/60 hover:text-white mb-4 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to history
        </Link>
        <h1 className="text-3xl font-bold">{session.topic}</h1>
        <div className="flex items-center gap-4 text-white/60 mt-2">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            {formatDate(session.start_time)}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {formatTime(session.start_time)} - {formatTime(session.end_time)}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <div className="text-white/60 text-sm">Duration</div>
          <div className="text-2xl font-bold">{Math.round(session.actual_minutes)}m</div>
          <div className="text-white/40 text-xs">of {session.planned_minutes}m planned</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-white/60 text-sm">Relevance</div>
          <div className={`text-2xl font-bold ${relevanceColor}`}>
            {Math.round(session.topic_relevance_score)}%
          </div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-white/60 text-sm">Breaks</div>
          <div className="text-2xl font-bold">{session.breaks.length}</div>
          <div className="text-white/40 text-xs">{Math.round(session.total_break_time / 60)}m total</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-white/60 text-sm">Status</div>
          <div className="mt-1">
            {session.topic_drift_detected || session.overconfidence_detected ? (
              <AlertTriangle className="w-6 h-6 text-yellow-400 mx-auto" />
            ) : (
              <CheckCircle className="w-6 h-6 text-green-400 mx-auto" />
            )}
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="card p-6">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-400" />
          Session Notes
        </h3>
        <ul className="space-y-2">
          {session.notes.map((note, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-blue-400 font-medium">{i + 1}.</span>
              <span className="text-white/90">{note}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* AI Summary */}
      <div className="card p-6">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <Target className="w-5 h-5 text-green-400" />
          AI Summary
        </h3>
        <p className="text-white/80">{session.ai_summary}</p>
      </div>

      {/* Warnings */}
      {(session.topic_drift_detected || session.overconfidence_detected) && (
        <div className="card p-6 border-yellow-500/30 bg-yellow-500/5">
          <h3 className="font-semibold mb-3 flex items-center gap-2 text-yellow-400">
            <AlertTriangle className="w-5 h-5" />
            Issues Detected
          </h3>
          <div className="space-y-3">
            {session.topic_drift_detected && (
              <div>
                <div className="font-medium text-yellow-300">Topic Drift</div>
                <p className="text-white/70">{session.drift_details}</p>
              </div>
            )}
            {session.overconfidence_detected && (
              <div>
                <div className="font-medium text-yellow-300">Overconfidence Warning</div>
                <p className="text-white/70">{session.overconfidence_details}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Focus Feedback */}
      <div className="card p-6">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-purple-400" />
          Focus Feedback
        </h3>
        <p className="text-white/80">{session.focus_feedback}</p>
      </div>

      {/* Revision Tasks */}
      {session.revision_tasks.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-blue-400" />
            Revision Tasks
          </h3>
          <ul className="space-y-2">
            {session.revision_tasks.map((task, i) => (
              <li key={i} className="flex items-start gap-2">
                <input type="checkbox" className="mt-1 accent-blue-500" />
                <span className="text-white/80">{task}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next Session Plan */}
      {session.next_session_plan && (
        <div className="card p-6 border-blue-500/30 bg-blue-500/5">
          <h3 className="font-semibold mb-2 text-blue-400">Recommended Next Session</h3>
          <p className="text-white/80">{session.next_session_plan}</p>
        </div>
      )}

      {/* Breaks Timeline */}
      {session.breaks.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Coffee className="w-5 h-5 text-amber-400" />
            Break Log
          </h3>
          <div className="space-y-2">
            {session.breaks.map((brk, i) => (
              <div key={i} className="flex items-center gap-4 text-sm">
                <span className="text-white/40">Break {i + 1}</span>
                <span className="text-white/60">
                  {formatTime(brk.start_time)} - {formatTime(brk.end_time)}
                </span>
                <span className="text-amber-400">
                  {Math.round(brk.duration_seconds / 60)}m
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
