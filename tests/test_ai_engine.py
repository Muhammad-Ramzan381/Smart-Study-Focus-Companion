"""
Tests for AIEngine local analysis functionality.
Tests the focus scoring and note analysis without Claude API.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from focus_companion import AIEngine


class TestLocalAnalysis:
    """Test AIEngine._analyze_locally method."""

    def test_basic_analysis_returns_required_fields(self):
        """Analysis should return summary, relevance, and feedback."""
        result = AIEngine._analyze_locally(
            topic="Python Basics",
            notes=["Learned about variables", "Functions are reusable code"],
            planned_mins=25,
            actual_mins=24,
            break_count=0,
            total_break_secs=0
        )

        assert "summary" in result
        assert "topic_relevance" in result
        assert "focus_feedback" in result

    def test_summary_contains_notes_content(self):
        """Summary should reflect the notes taken."""
        notes = ["Binary search divides array in half", "Time complexity is O(log n)"]
        result = AIEngine._analyze_locally(
            topic="Binary Search",
            notes=notes,
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        # Summary should mention some note content
        summary_lower = result["summary"].lower()
        assert "binary" in summary_lower or "search" in summary_lower or "array" in summary_lower

    def test_high_relevance_with_matching_topic(self):
        """Notes matching topic should get high relevance score."""
        result = AIEngine._analyze_locally(
            topic="Machine Learning",
            notes=[
                "Machine learning uses algorithms to learn from data",
                "Supervised learning requires labeled examples",
                "Neural networks are inspired by the brain"
            ],
            planned_mins=30,
            actual_mins=30,
            break_count=0,
            total_break_secs=0
        )

        # Should have reasonable relevance since notes mention topic
        assert result["topic_relevance"] >= 50

    def test_low_relevance_with_unrelated_notes(self):
        """Notes not matching topic should get lower relevance."""
        result = AIEngine._analyze_locally(
            topic="Quantum Physics",
            notes=[
                "Made a sandwich for lunch",
                "Called my friend about the party",
                "Need to buy groceries"
            ],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        # Should have low relevance since notes don't match topic
        assert result["topic_relevance"] < 70

    def test_empty_notes_handling(self):
        """Should handle empty notes gracefully."""
        result = AIEngine._analyze_locally(
            topic="History",
            notes=[],
            planned_mins=25,
            actual_mins=20,
            break_count=0,
            total_break_secs=0
        )

        assert result["summary"] is not None
        assert result["topic_relevance"] is not None
        assert result["focus_feedback"] is not None


class TestFocusFeedback:
    """Test focus feedback generation."""

    def test_feedback_on_full_completion(self):
        """Completing full time should get positive feedback."""
        result = AIEngine._analyze_locally(
            topic="Study",
            notes=["Point 1", "Point 2", "Point 3"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        feedback_lower = result["focus_feedback"].lower()
        # Should mention good time management
        assert "time" in feedback_lower or "great" in feedback_lower or "good" in feedback_lower

    def test_feedback_on_partial_completion(self):
        """Partial completion should mention completion percentage."""
        result = AIEngine._analyze_locally(
            topic="Study",
            notes=["Note 1"],
            planned_mins=30,
            actual_mins=15,
            break_count=0,
            total_break_secs=0
        )

        # Should mention completion or suggest shorter goals
        assert "%" in result["focus_feedback"] or "goal" in result["focus_feedback"].lower()

    def test_feedback_on_good_notes(self):
        """Having 3+ notes should get positive note feedback."""
        result = AIEngine._analyze_locally(
            topic="Topic",
            notes=["Note 1", "Note 2", "Note 3", "Note 4"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        feedback_lower = result["focus_feedback"].lower()
        assert "note" in feedback_lower

    def test_feedback_on_few_notes(self):
        """Having few notes should suggest capturing more."""
        result = AIEngine._analyze_locally(
            topic="Topic",
            notes=["Only one note"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        feedback_lower = result["focus_feedback"].lower()
        # Should suggest more notes
        assert "more" in feedback_lower or "note" in feedback_lower


class TestRelevanceScoring:
    """Test topic relevance score calculation."""

    def test_relevance_score_range(self):
        """Relevance score should be between 0 and 100."""
        result = AIEngine._analyze_locally(
            topic="Any Topic",
            notes=["Some notes here"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        assert 0 <= result["topic_relevance"] <= 100

    def test_direct_topic_mention_increases_relevance(self):
        """Mentioning the topic directly should increase relevance."""
        result_with_topic = AIEngine._analyze_locally(
            topic="Recursion",
            notes=["Recursion is when a function calls itself"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        result_without_topic = AIEngine._analyze_locally(
            topic="Recursion",
            notes=["Functions can do various things"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        assert result_with_topic["topic_relevance"] >= result_without_topic["topic_relevance"]

    def test_longer_notes_boost_relevance(self):
        """Detailed notes should have some positive effect on relevance."""
        result_detailed = AIEngine._analyze_locally(
            topic="Algorithms",
            notes=[
                "Algorithms are step by step procedures for solving problems",
                "Time complexity measures how runtime grows with input size",
                "Space complexity measures memory usage"
            ],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        result_brief = AIEngine._analyze_locally(
            topic="Algorithms",
            notes=["stuff"],
            planned_mins=25,
            actual_mins=25,
            break_count=0,
            total_break_secs=0
        )

        # Detailed notes should have equal or higher relevance
        assert result_detailed["topic_relevance"] >= result_brief["topic_relevance"]

