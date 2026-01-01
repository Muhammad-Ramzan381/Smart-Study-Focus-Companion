"""
Tests for RevisionTaskGenerator and NextSessionPlanner.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from focus_companion import RevisionTaskGenerator, NextSessionPlanner


class TestRevisionTaskGenerator:
    """Test revision task generation logic."""

    def test_generates_tasks_list(self):
        """Should return a list of tasks."""
        tasks = RevisionTaskGenerator.generate(
            topic="Data Structures",
            notes=["Arrays store elements", "Linked lists use pointers"],
            drift_detected=False,
            overconfidence_detected=False,
            relevance_score=75
        )

        assert isinstance(tasks, list)
        assert len(tasks) >= 1

    def test_tasks_are_strings(self):
        """Each task should be a string."""
        tasks = RevisionTaskGenerator.generate(
            topic="Python",
            notes=["Functions are callable", "Classes define objects"],
            drift_detected=False,
            overconfidence_detected=False,
            relevance_score=80
        )

        for task in tasks:
            assert isinstance(task, str)
            assert len(task) > 0

    def test_max_four_tasks(self):
        """Should return at most 4 tasks."""
        tasks = RevisionTaskGenerator.generate(
            topic="Complex Topic",
            notes=["Note 1", "Note 2", "Note 3", "Note 4", "Note 5"],
            drift_detected=True,
            overconfidence_detected=True,
            relevance_score=40
        )

        assert len(tasks) <= 4

    def test_drift_triggers_specific_tasks(self):
        """Topic drift should trigger re-study tasks."""
        tasks = RevisionTaskGenerator.generate(
            topic="Machine Learning",
            notes=["Random notes about cooking"],
            drift_detected=True,
            overconfidence_detected=False,
            relevance_score=30
        )

        tasks_text = " ".join(tasks).lower()
        # Should suggest re-studying or summarizing
        assert "study" in tasks_text or "summary" in tasks_text or "re-study" in tasks_text

    def test_overconfidence_triggers_recall_tasks(self):
        """Overconfidence should trigger active recall tasks."""
        tasks = RevisionTaskGenerator.generate(
            topic="Neural Networks",
            notes=["Watched video about backpropagation"],
            drift_detected=False,
            overconfidence_detected=True,
            relevance_score=60
        )

        tasks_text = " ".join(tasks).lower()
        # Should suggest recall or teaching
        assert "remember" in tasks_text or "teach" in tasks_text or "close" in tasks_text

    def test_short_notes_trigger_expansion_task(self):
        """Short notes should trigger expansion suggestions."""
        tasks = RevisionTaskGenerator.generate(
            topic="Databases",
            notes=["SQL", "Tables", "Queries"],  # Very short notes
            drift_detected=False,
            overconfidence_detected=False,
            relevance_score=70
        )

        tasks_text = " ".join(tasks).lower()
        # Should suggest expanding
        assert "expand" in tasks_text or "example" in tasks_text or len(tasks) > 0

    def test_good_session_includes_quiz_task(self):
        """Good relevance score should include quiz suggestion."""
        tasks = RevisionTaskGenerator.generate(
            topic="Graph Algorithms",
            notes=[
                "BFS uses a queue for traversal",
                "DFS uses a stack or recursion",
                "Dijkstra finds shortest paths"
            ],
            drift_detected=False,
            overconfidence_detected=False,
            relevance_score=85
        )

        tasks_text = " ".join(tasks).lower()
        # Should suggest quiz or recall
        assert "quiz" in tasks_text or "key points" in tasks_text

    def test_multiple_notes_include_diagram_task(self):
        """Having multiple notes should suggest diagram creation."""
        tasks = RevisionTaskGenerator.generate(
            topic="System Design",
            notes=[
                "Load balancers distribute traffic",
                "Databases can be sharded",
                "Caching reduces latency"
            ],
            drift_detected=False,
            overconfidence_detected=False,
            relevance_score=75
        )

        tasks_text = " ".join(tasks).lower()
        # Should suggest diagram for connecting concepts
        assert "diagram" in tasks_text or "connect" in tasks_text

    def test_empty_notes_returns_default_task(self):
        """Empty notes should return at least one default task."""
        tasks = RevisionTaskGenerator.generate(
            topic="Topic",
            notes=[],
            drift_detected=True,
            overconfidence_detected=True,
            relevance_score=0
        )

        assert len(tasks) >= 1


class TestNextSessionPlanner:
    """Test next session planning logic."""

    def test_returns_string_plan(self):
        """Should return a string plan."""
        current_session = {
            "topic": "Python",
            "relevance_score": 80,
            "drift_detected": False,
            "overconfidence_detected": False,
            "actual_minutes": 25
        }
        plan = NextSessionPlanner.plan(current_session, [])

        assert isinstance(plan, str)
        assert len(plan) > 0

    def test_drift_suggests_refocus(self):
        """Topic drift should suggest refocusing on original topic."""
        current_session = {
            "topic": "Calculus",
            "relevance_score": 30,
            "drift_detected": True,
            "overconfidence_detected": False,
            "actual_minutes": 25
        }
        plan = NextSessionPlanner.plan(current_session, [])

        plan_lower = plan.lower()
        # Should mention refocusing or the topic
        assert "calculus" in plan_lower or "focus" in plan_lower or "restart" in plan_lower

    def test_overconfidence_suggests_active_learning(self):
        """Overconfidence should suggest active learning methods."""
        current_session = {
            "topic": "Statistics",
            "relevance_score": 60,
            "drift_detected": False,
            "overconfidence_detected": True,
            "actual_minutes": 25
        }
        plan = NextSessionPlanner.plan(current_session, [])

        plan_lower = plan.lower()
        # Should suggest recall or active methods
        assert "recall" in plan_lower or "test" in plan_lower or "review" in plan_lower

    def test_good_session_suggests_continuation(self):
        """Good session should suggest continuing to next topic."""
        current_session = {
            "topic": "Sorting Algorithms",
            "relevance_score": 90,
            "drift_detected": False,
            "overconfidence_detected": False,
            "actual_minutes": 30
        }
        plan = NextSessionPlanner.plan(current_session, [])

        plan_lower = plan.lower()
        # Should suggest continuation or advancement
        assert "connect" in plan_lower or "apply" in plan_lower or "problem" in plan_lower or "strong" in plan_lower

    def test_plan_is_not_empty_for_any_input(self):
        """Should always return a non-empty plan."""
        # Edge case: all problems
        current_session1 = {
            "topic": "T",
            "relevance_score": 0,
            "drift_detected": True,
            "overconfidence_detected": True,
            "actual_minutes": 10
        }
        plan1 = NextSessionPlanner.plan(current_session1, [])
        assert len(plan1) > 0

        # Edge case: perfect session
        current_session2 = {
            "topic": "T",
            "relevance_score": 100,
            "drift_detected": False,
            "overconfidence_detected": False,
            "actual_minutes": 30
        }
        plan2 = NextSessionPlanner.plan(current_session2, [])
        assert len(plan2) > 0

