"""
Tests for data persistence (save/load sessions) and StudySession model.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from focus_companion import StudySession, load_sessions, save_session, SESSIONS_FILE


class TestStudySessionModel:
    """Test StudySession dataclass."""

    def test_create_session(self):
        """Should create a session with all fields."""
        session = StudySession(
            id="test-123",
            topic="Python Basics",
            planned_minutes=25,
            actual_minutes=24.5,
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T10:25:00",
            breaks=[],
            total_break_time=0,
            notes=["Note 1", "Note 2"],
            ai_summary="Learned about Python",
            topic_relevance_score=85.0,
            focus_feedback="Good session",
            completed=True
        )

        assert session.id == "test-123"
        assert session.topic == "Python Basics"
        assert session.planned_minutes == 25
        assert session.actual_minutes == 24.5
        assert len(session.notes) == 2

    def test_phase2_fields_default(self):
        """Phase 2 fields should have defaults."""
        session = StudySession(
            id="test",
            topic="Topic",
            planned_minutes=25,
            actual_minutes=25,
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T10:25:00",
            breaks=[],
            total_break_time=0,
            notes=[],
            ai_summary="",
            topic_relevance_score=0,
            focus_feedback="",
            completed=True
        )

        assert session.topic_drift_detected is False
        assert session.drift_details == ""
        assert session.overconfidence_detected is False
        assert session.overconfidence_details == ""
        assert session.revision_tasks == []
        assert session.next_session_plan == ""

    def test_to_dict(self):
        """Should convert session to dictionary."""
        session = StudySession(
            id="test-456",
            topic="JavaScript",
            planned_minutes=30,
            actual_minutes=28.0,
            start_time="2024-01-15T14:00:00",
            end_time="2024-01-15T14:28:00",
            breaks=[{"start": "14:10", "end": "14:12", "duration_seconds": 120}],
            total_break_time=120,
            notes=["Async/await", "Promises"],
            ai_summary="JavaScript async patterns",
            topic_relevance_score=90.0,
            focus_feedback="Excellent focus",
            completed=True,
            topic_drift_detected=False,
            drift_details="",
            overconfidence_detected=True,
            overconfidence_details="Mostly reading",
            revision_tasks=["Practice coding"],
            next_session_plan="Build a project"
        )

        result = session.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "test-456"
        assert result["topic"] == "JavaScript"
        assert result["overconfidence_detected"] is True
        assert "Practice coding" in result["revision_tasks"]

    def test_from_dict(self):
        """Should recreate session from dictionary."""
        data = {
            "id": "test-789",
            "topic": "React",
            "planned_minutes": 45,
            "actual_minutes": 42.5,
            "start_time": "2024-01-16T09:00:00",
            "end_time": "2024-01-16T09:42:30",
            "breaks": [],
            "total_break_time": 0,
            "notes": ["Components", "Props", "State"],
            "ai_summary": "React fundamentals",
            "topic_relevance_score": 88.0,
            "focus_feedback": "Good",
            "completed": True,
            "topic_drift_detected": True,
            "drift_details": "Some tangent",
            "overconfidence_detected": False,
            "overconfidence_details": "",
            "revision_tasks": ["Review components"],
            "next_session_plan": "Hooks"
        }

        session = StudySession.from_dict(data)

        assert session.id == "test-789"
        assert session.topic == "React"
        assert session.topic_drift_detected is True
        assert len(session.notes) == 3

    def test_from_dict_with_missing_phase2_fields(self):
        """Should handle old data without Phase 2 fields."""
        # Simulate old data format before Phase 2
        data = {
            "id": "old-session",
            "topic": "Old Topic",
            "planned_minutes": 25,
            "actual_minutes": 25,
            "start_time": "2024-01-10T10:00:00",
            "end_time": "2024-01-10T10:25:00",
            "breaks": [],
            "total_break_time": 0,
            "notes": ["Old note"],
            "ai_summary": "Old summary",
            "topic_relevance_score": 70.0,
            "focus_feedback": "OK",
            "completed": True
            # Missing Phase 2 fields
        }

        session = StudySession.from_dict(data)

        assert session.id == "old-session"
        assert session.topic_drift_detected is False
        assert session.overconfidence_detected is False
        assert session.revision_tasks == []

    def test_round_trip(self):
        """Converting to dict and back should preserve data."""
        original = StudySession(
            id="round-trip",
            topic="Testing",
            planned_minutes=20,
            actual_minutes=19.5,
            start_time="2024-01-17T11:00:00",
            end_time="2024-01-17T11:19:30",
            breaks=[{"start": "11:10", "end": "11:11", "duration_seconds": 60}],
            total_break_time=60,
            notes=["Test 1", "Test 2"],
            ai_summary="Testing round trip",
            topic_relevance_score=95.0,
            focus_feedback="Great",
            completed=True,
            topic_drift_detected=True,
            drift_details="Minor drift",
            overconfidence_detected=True,
            overconfidence_details="Some overconfidence",
            revision_tasks=["Task A", "Task B"],
            next_session_plan="Continue testing"
        )

        data = original.to_dict()
        restored = StudySession.from_dict(data)

        assert restored.id == original.id
        assert restored.topic == original.topic
        assert restored.actual_minutes == original.actual_minutes
        assert restored.notes == original.notes
        assert restored.topic_drift_detected == original.topic_drift_detected
        assert restored.revision_tasks == original.revision_tasks


class TestJSONSerialization:
    """Test JSON serialization of session data."""

    def test_session_is_json_serializable(self):
        """Session dict should be JSON serializable."""
        session = StudySession(
            id="json-test",
            topic="Serialization",
            planned_minutes=25,
            actual_minutes=25,
            start_time="2024-01-18T10:00:00",
            end_time="2024-01-18T10:25:00",
            breaks=[],
            total_break_time=0,
            notes=["JSON works"],
            ai_summary="Testing JSON",
            topic_relevance_score=80.0,
            focus_feedback="Good",
            completed=True
        )

        # Should not raise
        json_str = json.dumps(session.to_dict())
        assert isinstance(json_str, str)

        # Should round-trip through JSON
        parsed = json.loads(json_str)
        restored = StudySession.from_dict(parsed)
        assert restored.id == session.id

    def test_complex_notes_serialize(self):
        """Notes with special characters should serialize."""
        session = StudySession(
            id="special-chars",
            topic="Edge Cases",
            planned_minutes=25,
            actual_minutes=25,
            start_time="2024-01-18T10:00:00",
            end_time="2024-01-18T10:25:00",
            breaks=[],
            total_break_time=0,
            notes=[
                "Quote: \"Hello\"",
                "Unicode: 日本語",
                "Emoji: 🎯",
                "Newline: line1\nline2"
            ],
            ai_summary="Special chars",
            topic_relevance_score=75.0,
            focus_feedback="OK",
            completed=True
        )

        json_str = json.dumps(session.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)
        restored = StudySession.from_dict(parsed)

        assert "日本語" in restored.notes[1]
        assert "🎯" in restored.notes[2]


class TestBreakDataStructure:
    """Test break tracking data structure."""

    def test_break_in_session(self):
        """Breaks should be stored correctly."""
        session = StudySession(
            id="break-test",
            topic="Breaks",
            planned_minutes=30,
            actual_minutes=28,
            start_time="2024-01-19T14:00:00",
            end_time="2024-01-19T14:30:00",
            breaks=[
                {
                    "start_time": "2024-01-19T14:10:00",
                    "end_time": "2024-01-19T14:12:00",
                    "duration_seconds": 120
                }
            ],
            total_break_time=120,
            notes=["Took a break"],
            ai_summary="Break test",
            topic_relevance_score=70.0,
            focus_feedback="Good",
            completed=True
        )

        assert len(session.breaks) == 1
        assert session.breaks[0]["duration_seconds"] == 120
        assert session.total_break_time == 120

    def test_multiple_breaks(self):
        """Multiple breaks should be tracked."""
        session = StudySession(
            id="multi-break",
            topic="Long Session",
            planned_minutes=60,
            actual_minutes=55,
            start_time="2024-01-19T10:00:00",
            end_time="2024-01-19T11:00:00",
            breaks=[
                {"start_time": "10:15", "end_time": "10:17", "duration_seconds": 120},
                {"start_time": "10:35", "end_time": "10:38", "duration_seconds": 180},
            ],
            total_break_time=300,
            notes=["Long session with breaks"],
            ai_summary="Breaks",
            topic_relevance_score=75.0,
            focus_feedback="Good pacing",
            completed=True
        )

        assert len(session.breaks) == 2
        assert session.total_break_time == 300


class TestSessionFieldValidation:
    """Test various field value scenarios."""

    def test_zero_minutes(self):
        """Should handle zero minutes session."""
        session = StudySession(
            id="zero-min",
            topic="Quick",
            planned_minutes=0,
            actual_minutes=0,
            start_time="2024-01-20T10:00:00",
            end_time="2024-01-20T10:00:00",
            breaks=[],
            total_break_time=0,
            notes=[],
            ai_summary="",
            topic_relevance_score=0,
            focus_feedback="",
            completed=False
        )

        assert session.actual_minutes == 0
        data = session.to_dict()
        restored = StudySession.from_dict(data)
        assert restored.actual_minutes == 0

    def test_very_long_topic(self):
        """Should handle long topic names."""
        long_topic = "Introduction to Advanced Machine Learning Algorithms and Deep Neural Network Architectures"
        session = StudySession(
            id="long-topic",
            topic=long_topic,
            planned_minutes=60,
            actual_minutes=55,
            start_time="2024-01-20T10:00:00",
            end_time="2024-01-20T11:00:00",
            breaks=[],
            total_break_time=0,
            notes=["Complex topic"],
            ai_summary="Long topic",
            topic_relevance_score=70.0,
            focus_feedback="OK",
            completed=True
        )

        assert session.topic == long_topic
        data = session.to_dict()
        restored = StudySession.from_dict(data)
        assert restored.topic == long_topic

    def test_empty_notes_list(self):
        """Should handle empty notes list."""
        session = StudySession(
            id="empty-notes",
            topic="No Notes",
            planned_minutes=25,
            actual_minutes=25,
            start_time="2024-01-20T10:00:00",
            end_time="2024-01-20T10:25:00",
            breaks=[],
            total_break_time=0,
            notes=[],
            ai_summary="No notes taken",
            topic_relevance_score=0,
            focus_feedback="Take more notes",
            completed=True
        )

        assert session.notes == []
        data = session.to_dict()
        restored = StudySession.from_dict(data)
        assert restored.notes == []

    def test_relevance_score_boundaries(self):
        """Should handle edge relevance scores."""
        # Max score
        session_max = StudySession(
            id="max-score",
            topic="Perfect",
            planned_minutes=25,
            actual_minutes=25,
            start_time="2024-01-20T10:00:00",
            end_time="2024-01-20T10:25:00",
            breaks=[],
            total_break_time=0,
            notes=["Perfect notes"],
            ai_summary="Perfect",
            topic_relevance_score=100.0,
            focus_feedback="Perfect",
            completed=True
        )

        assert session_max.topic_relevance_score == 100.0

        # Min score
        session_min = StudySession(
            id="min-score",
            topic="Zero",
            planned_minutes=25,
            actual_minutes=25,
            start_time="2024-01-20T11:00:00",
            end_time="2024-01-20T11:25:00",
            breaks=[],
            total_break_time=0,
            notes=[],
            ai_summary="Nothing",
            topic_relevance_score=0.0,
            focus_feedback="Try harder",
            completed=True
        )

        assert session_min.topic_relevance_score == 0.0

