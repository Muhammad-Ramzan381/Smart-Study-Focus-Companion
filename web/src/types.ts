// Type definitions for Study Companion

export interface Break {
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

export interface Session {
  id: string;
  topic: string;
  planned_minutes: number;
  actual_minutes: number;
  start_time: string;
  end_time: string;
  breaks: Break[];
  total_break_time: number;
  notes: string[];
  ai_summary: string;
  topic_relevance_score: number;
  focus_feedback: string;
  completed: boolean;
  topic_drift_detected: boolean;
  drift_details: string;
  overconfidence_detected: boolean;
  overconfidence_details: string;
  revision_tasks: string[];
  next_session_plan: string;
}

export interface DailyBreakdown {
  day: string;
  minutes: number;
  sessions: number;
  avg_score: number;
}

export interface TopicAnalysis {
  topic: string;
  time: number;
  sessions: number;
  avg_score: number;
  issues: number;
  understanding: 'good' | 'medium' | 'low';
}

export interface ProblemArea {
  topic: string;
  sessions: number;
  issues: string[];
  priority: 'high' | 'medium';
}

export interface WeeklyReport {
  period: {
    start: string;
    end: string;
  };
  overview: {
    this_week: {
      time: number;
      sessions: number;
      avg_relevance: number;
      issues: number;
    };
    last_week: {
      time: number;
      sessions: number;
      avg_relevance: number;
      issues: number;
    };
    time_change: number;
    sessions_change: number;
  };
  daily_breakdown: DailyBreakdown[];
  topic_analysis: TopicAnalysis[];
  time_vs_retention: {
    short_sessions: { count: number; avg_score: number };
    medium_sessions: { count: number; avg_score: number };
    long_sessions: { count: number; avg_score: number };
    optimal_duration: string;
  };
  problem_areas: ProblemArea[];
  recommendations: string[];
  streak: number;
}

export interface Stats {
  total_sessions: number;
  total_hours: number;
  avg_relevance: number;
  current_streak: number;
}

export interface SessionFormData {
  topic: string;
  planned_minutes: number;
  actual_minutes: number;
  notes: string[];
  breaks: Break[];
  start_time: string;
}
