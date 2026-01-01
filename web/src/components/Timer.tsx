import { useState, useEffect, useCallback } from 'react';
import { Play, Pause, Coffee, Square, RotateCcw } from 'lucide-react';

interface TimerProps {
  plannedMinutes: number;
  onComplete: (actualSeconds: number, breaks: BreakRecord[]) => void;
  onCancel: () => void;
}

interface BreakRecord {
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

type TimerState = 'ready' | 'running' | 'paused' | 'break' | 'completed';

export function Timer({ plannedMinutes, onComplete, onCancel }: TimerProps) {
  const [state, setState] = useState<TimerState>('ready');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [breakStartTime, setBreakStartTime] = useState<Date | null>(null);
  const [breaks, setBreaks] = useState<BreakRecord[]>([]);
  const [totalBreakSeconds, setTotalBreakSeconds] = useState(0);

  const plannedSeconds = plannedMinutes * 60;
  const remainingSeconds = Math.max(0, plannedSeconds - elapsedSeconds);
  const progress = (elapsedSeconds / plannedSeconds) * 100;

  // Timer tick
  useEffect(() => {
    if (state !== 'running') return;

    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [state]);

  // Break timer
  useEffect(() => {
    if (state !== 'break' || !breakStartTime) return;

    const interval = setInterval(() => {
      const now = new Date();
      const breakDuration = Math.floor((now.getTime() - breakStartTime.getTime()) / 1000);
      setTotalBreakSeconds(
        breaks.reduce((sum, b) => sum + b.duration_seconds, 0) + breakDuration
      );
    }, 1000);

    return () => clearInterval(interval);
  }, [state, breakStartTime, breaks]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStart = () => setState('running');

  const handlePause = () => setState('paused');

  const handleResume = () => setState('running');

  const handleBreak = () => {
    setState('break');
    setBreakStartTime(new Date());
  };

  const handleEndBreak = () => {
    if (breakStartTime) {
      const endTime = new Date();
      const duration = Math.floor((endTime.getTime() - breakStartTime.getTime()) / 1000);
      setBreaks(prev => [
        ...prev,
        {
          start_time: breakStartTime.toISOString(),
          end_time: endTime.toISOString(),
          duration_seconds: duration,
        },
      ]);
    }
    setBreakStartTime(null);
    setState('running');
  };

  const handleComplete = useCallback(() => {
    setState('completed');
    onComplete(elapsedSeconds, breaks);
  }, [elapsedSeconds, breaks, onComplete]);

  // Reset function available for future use
  const _handleReset = () => {
    setState('ready');
    setElapsedSeconds(0);
    setBreaks([]);
    setTotalBreakSeconds(0);
    setBreakStartTime(null);
  };
  void _handleReset; // Suppress unused warning

  return (
    <div className="card p-8 text-center">
      {/* Progress Ring */}
      <div className="relative w-64 h-64 mx-auto mb-6">
        <svg className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="128"
            cy="128"
            r="120"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="8"
          />
          {/* Progress circle */}
          <circle
            cx="128"
            cy="128"
            r="120"
            fill="none"
            stroke={state === 'break' ? '#f59e0b' : '#3b82f6'}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 120}`}
            strokeDashoffset={`${2 * Math.PI * 120 * (1 - Math.min(progress, 100) / 100)}`}
            className="transition-all duration-1000"
          />
        </svg>

        {/* Timer display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {state === 'break' ? (
            <>
              <Coffee className="w-8 h-8 text-amber-400 mb-2" />
              <div className="text-4xl font-bold timer-display text-amber-400">
                {formatTime(
                  breakStartTime
                    ? Math.floor((Date.now() - breakStartTime.getTime()) / 1000)
                    : 0
                )}
              </div>
              <div className="text-white/60 text-sm mt-1">Break time</div>
            </>
          ) : (
            <>
              <div className="text-5xl font-bold timer-display">
                {elapsedSeconds >= plannedSeconds
                  ? formatTime(elapsedSeconds)
                  : formatTime(remainingSeconds)}
              </div>
              <div className="text-white/60 text-sm mt-2">
                {elapsedSeconds >= plannedSeconds ? 'Overtime' : 'remaining'}
              </div>
              {elapsedSeconds >= plannedSeconds && (
                <div className="text-green-400 text-sm mt-1">
                  +{formatTime(elapsedSeconds - plannedSeconds)} extra
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="flex justify-center gap-8 mb-6 text-sm">
        <div>
          <div className="text-white/60">Studied</div>
          <div className="text-xl font-semibold">{formatTime(elapsedSeconds)}</div>
        </div>
        <div>
          <div className="text-white/60">Breaks</div>
          <div className="text-xl font-semibold">{breaks.length} ({formatTime(totalBreakSeconds)})</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex justify-center gap-3">
        {state === 'ready' && (
          <button
            onClick={handleStart}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold transition"
          >
            <Play className="w-5 h-5" />
            Start Focus
          </button>
        )}

        {state === 'running' && (
          <>
            <button
              onClick={handlePause}
              className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-4 py-3 rounded-xl transition"
            >
              <Pause className="w-5 h-5" />
              Pause
            </button>
            <button
              onClick={handleBreak}
              className="flex items-center gap-2 bg-amber-600 hover:bg-amber-700 px-4 py-3 rounded-xl transition"
            >
              <Coffee className="w-5 h-5" />
              Take Break
            </button>
            <button
              onClick={handleComplete}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-3 rounded-xl transition"
            >
              <Square className="w-5 h-5" />
              End Session
            </button>
          </>
        )}

        {state === 'paused' && (
          <>
            <button
              onClick={handleResume}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold transition"
            >
              <Play className="w-5 h-5" />
              Resume
            </button>
            <button
              onClick={handleComplete}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-3 rounded-xl transition"
            >
              <Square className="w-5 h-5" />
              End Session
            </button>
          </>
        )}

        {state === 'break' && (
          <button
            onClick={handleEndBreak}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold transition"
          >
            <Play className="w-5 h-5" />
            Resume Study
          </button>
        )}
      </div>

      {/* Cancel button */}
      {state !== 'completed' && state !== 'ready' && (
        <button
          onClick={onCancel}
          className="mt-4 text-white/40 hover:text-white/60 text-sm transition flex items-center gap-1 mx-auto"
        >
          <RotateCcw className="w-3 h-3" />
          Cancel session
        </button>
      )}
    </div>
  );
}
