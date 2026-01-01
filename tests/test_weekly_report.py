"""
Tests for WeeklyReportGenerator and CLIChart visualization.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from focus_companion import WeeklyReportGenerator, CLIChart, StudySession


def create_test_session(
    topic: str = "Test Topic",
    actual_minutes: float = 25.0,
    relevance_score: float = 75.0,
    drift_detected: bool = False,
    overconfidence_detected: bool = False,
    days_ago: int = 0
) -> StudySession:
    """Helper to create test session objects."""
    session_time = datetime.now() - timedelta(days=days_ago)
    return StudySession(
        id=f"test-{session_time.timestamp()}",
        topic=topic,
        planned_minutes=30,
        actual_minutes=actual_minutes,
        start_time=session_time.isoformat(),
        end_time=(session_time + timedelta(minutes=actual_minutes)).isoformat(),
        breaks=[],
        total_break_time=0,
        notes=["Test note 1", "Test note 2"],
        ai_summary="Test summary",
        topic_relevance_score=relevance_score,
        focus_feedback="Good job",
        completed=True,
        topic_drift_detected=drift_detected,
        drift_details="Drift details" if drift_detected else "",
        overconfidence_detected=overconfidence_detected,
        overconfidence_details="Overconfidence details" if overconfidence_detected else "",
        revision_tasks=["Task 1"],
        next_session_plan="Plan"
    )


class TestWeeklyReportGeneration:
    """Test WeeklyReportGenerator.generate method."""

    def test_returns_required_sections(self):
        """Report should contain all required sections."""
        sessions = [create_test_session(days_ago=i) for i in range(3)]
        report = WeeklyReportGenerator.generate(sessions)

        assert "period" in report
        assert "overview" in report
        assert "daily_breakdown" in report
        assert "topic_analysis" in report
        assert "time_vs_retention" in report
        assert "problem_areas" in report
        assert "recommendations" in report
        assert "streak" in report

    def test_empty_sessions_handling(self):
        """Should handle empty session list gracefully."""
        report = WeeklyReportGenerator.generate([])

        assert report["overview"]["this_week"]["time"] == 0
        assert report["overview"]["this_week"]["sessions"] == 0
        assert len(report["daily_breakdown"]) == 7  # Still has all days

    def test_period_is_current_week(self):
        """Period should represent current week."""
        sessions = [create_test_session()]
        report = WeeklyReportGenerator.generate(sessions)

        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        assert report["period"]["start"] == week_start.isoformat()
        assert report["period"]["end"] == week_end.isoformat()


class TestOverviewCalculation:
    """Test the overview statistics calculation."""

    def test_calculates_total_time(self):
        """Should sum up all session times."""
        sessions = [
            create_test_session(actual_minutes=25, days_ago=0),
            create_test_session(actual_minutes=30, days_ago=1),
            create_test_session(actual_minutes=20, days_ago=2),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        assert report["overview"]["this_week"]["time"] == 75

    def test_counts_sessions(self):
        """Should count total sessions within the week."""
        # Create sessions that are all within the current week
        # Use days_ago based on current weekday to ensure they're in this week
        today_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
        # Create sessions only for days from start of week to today
        sessions = [create_test_session(days_ago=i) for i in range(today_weekday + 1)]
        report = WeeklyReportGenerator.generate(sessions)

        assert report["overview"]["this_week"]["sessions"] == today_weekday + 1

    def test_calculates_average_relevance(self):
        """Should calculate average relevance score."""
        sessions = [
            create_test_session(relevance_score=80, days_ago=0),
            create_test_session(relevance_score=60, days_ago=1),
            create_test_session(relevance_score=70, days_ago=2),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        assert report["overview"]["this_week"]["avg_relevance"] == 70

    def test_counts_issues(self):
        """Should count sessions with issues."""
        sessions = [
            create_test_session(drift_detected=True, days_ago=0),
            create_test_session(overconfidence_detected=True, days_ago=1),
            create_test_session(days_ago=2),  # No issues
        ]
        report = WeeklyReportGenerator.generate(sessions)

        assert report["overview"]["this_week"]["issues"] == 2


class TestDailyBreakdown:
    """Test daily breakdown calculation."""

    def test_has_seven_days(self):
        """Should have breakdown for all 7 days."""
        sessions = [create_test_session()]
        report = WeeklyReportGenerator.generate(sessions)

        assert len(report["daily_breakdown"]) == 7

    def test_day_names_correct(self):
        """Should have correct day names."""
        sessions = [create_test_session()]
        report = WeeklyReportGenerator.generate(sessions)

        day_names = [d["day"] for d in report["daily_breakdown"]]
        assert day_names == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def test_accumulates_daily_minutes(self):
        """Should accumulate minutes for same day."""
        # Create two sessions for today
        sessions = [
            create_test_session(actual_minutes=20, days_ago=0),
            create_test_session(actual_minutes=25, days_ago=0),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        today_idx = datetime.now().weekday()
        assert report["daily_breakdown"][today_idx]["minutes"] == 45


class TestTopicAnalysis:
    """Test topic-level analysis."""

    def test_groups_by_topic(self):
        """Should group sessions by topic."""
        sessions = [
            create_test_session(topic="Python", days_ago=0),
            create_test_session(topic="Python", days_ago=1),
            create_test_session(topic="JavaScript", days_ago=2),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        topics = [t["topic"] for t in report["topic_analysis"]]
        assert "Python" in topics
        assert "JavaScript" in topics

    def test_calculates_topic_time(self):
        """Should calculate total time per topic."""
        sessions = [
            create_test_session(topic="Python", actual_minutes=30, days_ago=0),
            create_test_session(topic="Python", actual_minutes=25, days_ago=1),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        python_topic = next(t for t in report["topic_analysis"] if t["topic"] == "Python")
        assert python_topic["time"] == 55

    def test_understanding_levels(self):
        """Should classify understanding level correctly."""
        sessions = [
            create_test_session(topic="Good", relevance_score=80, days_ago=0),
            create_test_session(topic="Medium", relevance_score=55, days_ago=1),
            create_test_session(topic="Low", relevance_score=40, days_ago=2),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        understanding_map = {t["topic"]: t["understanding"] for t in report["topic_analysis"]}
        assert understanding_map["Good"] == "good"
        assert understanding_map["Medium"] == "medium"
        assert understanding_map["Low"] == "low"


class TestTimeVsRetention:
    """Test time vs retention analysis."""

    def test_returns_session_buckets(self):
        """Should return short, medium, long session buckets."""
        sessions = [create_test_session()]
        report = WeeklyReportGenerator.generate(sessions)

        tvr = report["time_vs_retention"]
        assert "short_sessions" in tvr
        assert "medium_sessions" in tvr
        assert "long_sessions" in tvr

    def test_categorizes_by_duration(self):
        """Should categorize sessions by duration correctly."""
        sessions = [
            create_test_session(actual_minutes=15, days_ago=0),  # Short
            create_test_session(actual_minutes=25, days_ago=1),  # Medium
            create_test_session(actual_minutes=45, days_ago=2),  # Long
        ]
        report = WeeklyReportGenerator.generate(sessions)

        tvr = report["time_vs_retention"]
        assert tvr["short_sessions"]["count"] == 1
        assert tvr["medium_sessions"]["count"] == 1
        assert tvr["long_sessions"]["count"] == 1

    def test_has_optimal_duration(self):
        """Should determine optimal session duration."""
        sessions = [create_test_session(days_ago=i) for i in range(5)]
        report = WeeklyReportGenerator.generate(sessions)

        assert "optimal_duration" in report["time_vs_retention"]


class TestProblemAreas:
    """Test problem area identification."""

    def test_identifies_low_score_topics(self):
        """Should flag topics with low scores."""
        sessions = [
            create_test_session(topic="Struggling", relevance_score=40, days_ago=0),
            create_test_session(topic="Struggling", relevance_score=45, days_ago=1),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        problem_topics = [p["topic"] for p in report["problem_areas"]]
        assert "Struggling" in problem_topics

    def test_identifies_drift_patterns(self):
        """Should flag topics with frequent drift."""
        sessions = [
            create_test_session(topic="Drifty", drift_detected=True, relevance_score=70, days_ago=0),
            create_test_session(topic="Drifty", drift_detected=True, relevance_score=70, days_ago=1),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        problem_topics = [p["topic"] for p in report["problem_areas"]]
        assert "Drifty" in problem_topics

    def test_good_topics_not_flagged(self):
        """Should not flag topics with good scores and no issues."""
        sessions = [
            create_test_session(topic="Great", relevance_score=85, days_ago=0),
            create_test_session(topic="Great", relevance_score=90, days_ago=1),
        ]
        report = WeeklyReportGenerator.generate(sessions)

        problem_topics = [p["topic"] for p in report["problem_areas"]]
        assert "Great" not in problem_topics


class TestCLIChart:
    """Test CLI chart visualization utilities."""

    def test_horizontal_bar_basic(self):
        """Should create basic horizontal bar."""
        result = CLIChart.horizontal_bar("Test", 50, 100, width=10)

        assert "Test" in result
        assert "50" in result
        assert "█" in result

    def test_horizontal_bar_full(self):
        """Full bar should be all filled."""
        result = CLIChart.horizontal_bar("Full", 100, 100, width=10)

        assert "██████████" in result

    def test_horizontal_bar_empty(self):
        """Empty bar should be all empty."""
        result = CLIChart.horizontal_bar("Empty", 0, 100, width=10)

        assert "░░░░░░░░░░" in result

    def test_horizontal_bar_zero_max(self):
        """Should handle zero max value."""
        result = CLIChart.horizontal_bar("Zero", 50, 0, width=10)

        # Should not crash, should show empty bar
        assert "░░░░░░░░░░" in result

    def test_sparkline_basic(self):
        """Should create sparkline from values."""
        result = CLIChart.sparkline([1, 2, 3, 4, 5])

        # Should contain various height characters
        assert len(result) >= 5

    def test_sparkline_empty(self):
        """Should handle empty values."""
        result = CLIChart.sparkline([])

        # Should return placeholder
        assert "─" in result

    def test_sparkline_single_value(self):
        """Should handle single value."""
        result = CLIChart.sparkline([50])

        assert len(result) >= 1

    def test_trend_arrow_up(self):
        """Should show up arrow for increase."""
        result = CLIChart.trend_arrow(120, 100)

        assert result == "↑"

    def test_trend_arrow_down(self):
        """Should show down arrow for decrease."""
        result = CLIChart.trend_arrow(80, 100)

        assert result == "↓"

    def test_trend_arrow_stable(self):
        """Should show right arrow for stable."""
        result = CLIChart.trend_arrow(102, 100)

        assert result == "→"

    def test_trend_arrow_zero_previous(self):
        """Should handle zero previous value."""
        result = CLIChart.trend_arrow(50, 0)

        assert result == "→"

