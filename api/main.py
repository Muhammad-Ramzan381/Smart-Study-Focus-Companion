"""
Smart Study & Focus Companion - FastAPI Backend
Modern REST API for the study tracker.
"""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import uuid

# Add parent directory to import focus_companion
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from focus_companion import (
    StudySession, load_sessions, save_session,
    TopicDriftDetector, OverconfidenceDetector,
    RevisionTaskGenerator, NextSessionPlanner,
    WeeklyReportGenerator, AIEngine
)

app = FastAPI(
    title="Study Companion API",
    description="AI-powered study tracking and focus analysis",
    version="1.0.0"
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class BreakData(BaseModel):
    start_time: str
    end_time: str
    duration_seconds: int


class SessionCreate(BaseModel):
    topic: str
    planned_minutes: int
    actual_minutes: float
    notes: List[str]
    breaks: List[BreakData] = []
    start_time: str


class SessionResponse(BaseModel):
    id: str
    topic: str
    planned_minutes: int
    actual_minutes: float
    start_time: str
    end_time: str
    breaks: List[dict]
    total_break_time: int
    notes: List[str]
    ai_summary: str
    topic_relevance_score: float
    focus_feedback: str
    completed: bool
    topic_drift_detected: bool
    drift_details: str
    overconfidence_detected: bool
    overconfidence_details: str
    revision_tasks: List[str]
    next_session_plan: str


class AnalysisResponse(BaseModel):
    summary: str
    topic_relevance: float
    focus_feedback: str
    drift: dict
    overconfidence: dict
    revision_tasks: List[str]
    next_session_plan: str


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/sessions", response_model=List[SessionResponse])
async def get_sessions():
    """Get all study sessions."""
    sessions = load_sessions()
    return [s.to_dict() for s in sessions]


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a specific session by ID."""
    sessions = load_sessions()
    session = next((s for s in sessions if s.id == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(data: SessionCreate):
    """Create a new study session with AI analysis."""
    # Calculate break stats
    breaks_list = [b.model_dump() for b in data.breaks]
    total_break_time = sum(b.duration_seconds for b in data.breaks)
    break_count = len(data.breaks)

    # Get all sessions for context
    all_sessions = load_sessions()

    # Run AI analysis
    analysis = AIEngine.full_analysis(
        topic=data.topic,
        notes=data.notes,
        planned_mins=data.planned_minutes,
        actual_mins=data.actual_minutes,
        break_count=break_count,
        total_break_secs=total_break_time,
        all_sessions=all_sessions
    )

    # Create session object
    session = StudySession(
        id=str(uuid.uuid4())[:8],
        topic=data.topic,
        planned_minutes=data.planned_minutes,
        actual_minutes=data.actual_minutes,
        start_time=data.start_time,
        end_time=datetime.now().isoformat(),
        breaks=breaks_list,
        total_break_time=total_break_time,
        notes=data.notes,
        ai_summary=analysis['summary'],
        topic_relevance_score=analysis['topic_relevance'],
        focus_feedback=analysis['focus_feedback'],
        completed=True,
        topic_drift_detected=analysis['drift']['detected'],
        drift_details=analysis['drift']['details'],
        overconfidence_detected=analysis['overconfidence']['detected'],
        overconfidence_details=analysis['overconfidence']['details'],
        revision_tasks=analysis['revision_tasks'],
        next_session_plan=analysis['next_session_plan']
    )

    # Save session
    save_session(session)

    return session.to_dict()


@app.get("/api/report")
async def get_weekly_report():
    """Get weekly study report with analytics."""
    sessions = load_sessions()
    report = WeeklyReportGenerator.generate(sessions)
    return report


@app.post("/api/analyze")
async def analyze_notes(data: SessionCreate) -> AnalysisResponse:
    """Analyze notes without saving session (preview)."""
    all_sessions = load_sessions()
    breaks_list = [b.model_dump() for b in data.breaks]
    total_break_time = sum(b.duration_seconds for b in data.breaks)
    break_count = len(data.breaks)

    analysis = AIEngine.full_analysis(
        topic=data.topic,
        notes=data.notes,
        planned_mins=data.planned_minutes,
        actual_mins=data.actual_minutes,
        break_count=break_count,
        total_break_secs=total_break_time,
        all_sessions=all_sessions
    )

    return analysis


@app.get("/api/stats")
async def get_stats():
    """Get quick stats for the header."""
    sessions = load_sessions()
    if not sessions:
        return {
            "total_sessions": 0,
            "total_hours": 0,
            "avg_relevance": 0,
            "current_streak": 0
        }

    report = WeeklyReportGenerator.generate(sessions)
    total_minutes = sum(s.actual_minutes for s in sessions)

    return {
        "total_sessions": len(sessions),
        "total_hours": round(total_minutes / 60, 1),
        "avg_relevance": round(report['overview']['this_week']['avg_relevance'], 1),
        "current_streak": report['streak']
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    # Note: reload=True requires passing app as string, but that doesn't work
    # with paths containing special characters. Use reload=False for stability.
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
