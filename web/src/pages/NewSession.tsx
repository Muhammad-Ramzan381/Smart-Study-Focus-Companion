import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, BookOpen, Play, Plus, X, CheckCircle, AlertTriangle, Target } from 'lucide-react';
import { Timer } from '../components/Timer';
import { api } from '../api';

type Phase = 'setup' | 'timer' | 'notes' | 'results';

interface BreakRecord {
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

interface AnalysisResult {
  summary: string;
  topic_relevance: number;
  focus_feedback: string;
  drift: { detected: boolean; details: string };
  overconfidence: { detected: boolean; details: string };
  revision_tasks: string[];
  next_session_plan: string;
}

const DURATION_OPTIONS = [15, 25, 30, 45, 60];

export function NewSession() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>('setup');

  // Setup state
  const [topic, setTopic] = useState('');
  const [plannedMinutes, setPlannedMinutes] = useState(25);

  // Session state
  const [startTime, setStartTime] = useState('');
  const [actualSeconds, setActualSeconds] = useState(0);
  const [breaks, setBreaks] = useState<BreakRecord[]>([]);

  // Notes state
  const [notes, setNotes] = useState<string[]>(['']);
  const [saving, setSaving] = useState(false);

  // Results state
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  const handleStartSession = () => {
    if (!topic.trim()) return;
    setStartTime(new Date().toISOString());
    setPhase('timer');
  };

  const handleTimerComplete = (seconds: number, sessionBreaks: BreakRecord[]) => {
    setActualSeconds(seconds);
    setBreaks(sessionBreaks);
    setPhase('notes');
  };

  const handleAddNote = () => {
    if (notes.length < 5) {
      setNotes([...notes, '']);
    }
  };

  const handleRemoveNote = (index: number) => {
    if (notes.length > 1) {
      setNotes(notes.filter((_, i) => i !== index));
    }
  };

  const handleNoteChange = (index: number, value: string) => {
    const newNotes = [...notes];
    newNotes[index] = value;
    setNotes(newNotes);
  };

  const handleSubmitNotes = async () => {
    const filledNotes = notes.filter(n => n.trim());
    if (filledNotes.length < 1) return;

    setSaving(true);
    try {
      const response = await api.createSession({
        topic,
        planned_minutes: plannedMinutes,
        actual_minutes: actualSeconds / 60,
        notes: filledNotes,
        breaks,
        start_time: startTime,
      });

      setAnalysis({
        summary: response.ai_summary,
        topic_relevance: response.topic_relevance_score,
        focus_feedback: response.focus_feedback,
        drift: {
          detected: response.topic_drift_detected,
          details: response.drift_details,
        },
        overconfidence: {
          detected: response.overconfidence_detected,
          details: response.overconfidence_details,
        },
        revision_tasks: response.revision_tasks,
        next_session_plan: response.next_session_plan,
      });
      setPhase('results');
    } catch (error) {
      console.error('Failed to save session:', error);
      alert('Failed to save session. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Setup Phase
  if (phase === 'setup') {
    return (
      <div className="max-w-xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-center">Start New Session</h1>

        <div className="card p-8 space-y-6">
          {/* Topic Input */}
          <div>
            <label className="flex items-center gap-2 text-white/80 mb-2">
              <BookOpen className="w-4 h-4" />
              What are you studying?
            </label>
            <input
              type="text"
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="e.g., Binary Search Trees, React Hooks, Calculus..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:border-blue-500 transition"
              autoFocus
            />
          </div>

          {/* Duration Selection */}
          <div>
            <label className="flex items-center gap-2 text-white/80 mb-3">
              <Clock className="w-4 h-4" />
              Planned duration
            </label>
            <div className="flex flex-wrap gap-2">
              {DURATION_OPTIONS.map(mins => (
                <button
                  key={mins}
                  onClick={() => setPlannedMinutes(mins)}
                  className={`px-4 py-2 rounded-lg font-medium transition ${
                    plannedMinutes === mins
                      ? 'bg-blue-600 text-white'
                      : 'bg-white/5 text-white/70 hover:bg-white/10'
                  }`}
                >
                  {mins} min
                </button>
              ))}
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={handleStartSession}
            disabled={!topic.trim()}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-4 rounded-xl font-semibold text-lg transition"
          >
            <Play className="w-5 h-5" />
            Start Focus Session
          </button>
        </div>
      </div>
    );
  }

  // Timer Phase
  if (phase === 'timer') {
    return (
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold">{topic}</h2>
          <p className="text-white/60">Focus session in progress</p>
        </div>

        <Timer
          plannedMinutes={plannedMinutes}
          onComplete={handleTimerComplete}
          onCancel={() => setPhase('setup')}
        />
      </div>
    );
  }

  // Notes Phase
  if (phase === 'notes') {
    return (
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold">What did you learn?</h2>
          <p className="text-white/60">
            Studied <span className="text-blue-400">{topic}</span> for{' '}
            <span className="text-green-400">{formatTime(actualSeconds)}</span>
          </p>
        </div>

        <div className="card p-6 space-y-4">
          <p className="text-white/70 text-sm">
            Write 3-5 bullet points about what you learned. Be specific!
          </p>

          {notes.map((note, index) => (
            <div key={index} className="flex gap-2">
              <span className="text-white/40 mt-3">{index + 1}.</span>
              <input
                type="text"
                value={note}
                onChange={e => handleNoteChange(index, e.target.value)}
                placeholder="What's one thing you learned?"
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:border-blue-500 transition"
                autoFocus={index === 0}
              />
              {notes.length > 1 && (
                <button
                  onClick={() => handleRemoveNote(index)}
                  className="text-white/30 hover:text-red-400 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          ))}

          {notes.length < 5 && (
            <button
              onClick={handleAddNote}
              className="flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm transition"
            >
              <Plus className="w-4 h-4" />
              Add another note
            </button>
          )}

          <button
            onClick={handleSubmitNotes}
            disabled={saving || notes.filter(n => n.trim()).length < 1}
            className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-4 rounded-xl font-semibold text-lg transition mt-4"
          >
            {saving ? (
              'Analyzing...'
            ) : (
              <>
                <CheckCircle className="w-5 h-5" />
                Complete Session
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Results Phase
  if (phase === 'results' && analysis) {
    const relevanceColor =
      analysis.topic_relevance >= 70
        ? 'text-green-400'
        : analysis.topic_relevance >= 50
        ? 'text-yellow-400'
        : 'text-red-400';

    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold">Session Complete!</h2>
          <p className="text-white/60">{topic}</p>
        </div>

        {/* Relevance Score */}
        <div className="card p-6 text-center">
          <div className="text-white/60 mb-2">Topic Relevance</div>
          <div className={`text-5xl font-bold ${relevanceColor}`}>
            {Math.round(analysis.topic_relevance)}%
          </div>
        </div>

        {/* Summary */}
        <div className="card p-6">
          <h3 className="font-semibold mb-2">Summary</h3>
          <p className="text-white/80">{analysis.summary}</p>
        </div>

        {/* Warnings */}
        {(analysis.drift.detected || analysis.overconfidence.detected) && (
          <div className="card p-6 border-yellow-500/30 bg-yellow-500/5">
            <h3 className="font-semibold mb-3 flex items-center gap-2 text-yellow-400">
              <AlertTriangle className="w-5 h-5" />
              Attention Needed
            </h3>
            <div className="space-y-3">
              {analysis.drift.detected && (
                <div className="flex items-start gap-2">
                  <Target className="w-4 h-4 text-yellow-400 mt-1 flex-shrink-0" />
                  <p className="text-white/80">{analysis.drift.details}</p>
                </div>
              )}
              {analysis.overconfidence.detected && (
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400 mt-1 flex-shrink-0" />
                  <p className="text-white/80">{analysis.overconfidence.details}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Focus Feedback */}
        <div className="card p-6">
          <h3 className="font-semibold mb-2">Focus Feedback</h3>
          <p className="text-white/80">{analysis.focus_feedback}</p>
        </div>

        {/* Revision Tasks */}
        {analysis.revision_tasks.length > 0 && (
          <div className="card p-6">
            <h3 className="font-semibold mb-3">Revision Tasks</h3>
            <ul className="space-y-2">
              {analysis.revision_tasks.map((task, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span className="text-white/80">{task}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Next Session */}
        {analysis.next_session_plan && (
          <div className="card p-6 border-blue-500/30 bg-blue-500/5">
            <h3 className="font-semibold mb-2 text-blue-400">Next Session</h3>
            <p className="text-white/80">{analysis.next_session_plan}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex-1 bg-white/10 hover:bg-white/20 px-6 py-3 rounded-xl font-semibold transition"
          >
            View Dashboard
          </button>
          <button
            onClick={() => {
              setPhase('setup');
              setTopic('');
              setNotes(['']);
              setAnalysis(null);
            }}
            className="flex-1 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold transition"
          >
            Start Another Session
          </button>
        </div>
      </div>
    );
  }

  return null;
}
