import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle, Clock, Target } from 'lucide-react';
import type { Session } from '../types';

interface SessionCardProps {
  session: Session;
}

export function SessionCard({ session }: SessionCardProps) {
  const hasIssues = session.topic_drift_detected || session.overconfidence_detected;
  const relevanceColor =
    session.topic_relevance_score >= 70
      ? 'text-green-400'
      : session.topic_relevance_score >= 50
      ? 'text-yellow-400'
      : 'text-red-400';

  return (
    <Link
      to={`/session/${session.id}`}
      className="block bg-white/5 hover:bg-white/10 rounded-xl p-4 transition border border-transparent hover:border-white/10"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="font-semibold text-lg">{session.topic}</div>
          <div className="flex items-center gap-4 text-sm text-white/60 mt-1">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {Math.round(session.actual_minutes)} min
            </span>
            <span>{session.start_time.slice(0, 10)}</span>
            <span>{session.notes.length} notes</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className={`text-2xl font-bold ${relevanceColor}`}>
              {Math.round(session.topic_relevance_score)}%
            </div>
            <div className="text-xs text-white/40">relevance</div>
          </div>

          {hasIssues ? (
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
          ) : (
            <CheckCircle className="w-5 h-5 text-green-400" />
          )}
        </div>
      </div>

      {/* Preview of issues */}
      {hasIssues && (
        <div className="mt-3 pt-3 border-t border-white/10 text-sm">
          {session.topic_drift_detected && (
            <div className="text-yellow-400/80 flex items-center gap-1">
              <Target className="w-3 h-3" />
              Topic drift detected
            </div>
          )}
          {session.overconfidence_detected && (
            <div className="text-yellow-400/80 flex items-center gap-1 mt-1">
              <AlertTriangle className="w-3 h-3" />
              Overconfidence warning
            </div>
          )}
        </div>
      )}
    </Link>
  );
}
