"""
Tests for AI detection engines:
- TopicDriftDetector
- OverconfidenceDetector
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from focus_companion import TopicDriftDetector, OverconfidenceDetector


class TestTopicDriftDetector:
    """Test cases for topic drift detection."""

    def test_no_drift_with_relevant_notes(self):
        """Notes that match topic should not trigger drift."""
        topic = "Binary Search"
        notes = [
            "Binary search requires a sorted array",
            "Time complexity is O(log n)",
            "Implemented both iterative and recursive versions"
        ]
        relevance_score = 85

        result = TopicDriftDetector.detect(topic, notes, relevance_score)

        assert result["detected"] is False
        assert result["severity"] == "none"

    def test_drift_with_low_relevance(self):
        """Low relevance score should trigger high severity drift."""
        topic = "Machine Learning"
        notes = [
            "Watched a video about cooking",
            "Learned some recipes",
            "Made dinner"
        ]
        relevance_score = 25

        result = TopicDriftDetector.detect(topic, notes, relevance_score)

        assert result["detected"] is True
        assert result["severity"] == "high"
        assert "low relevance" in result["details"].lower()

    def test_drift_with_medium_relevance(self):
        """Medium relevance should trigger medium severity drift."""
        topic = "Data Structures"
        notes = [
            "Something about arrays",
            "Also looked at some code"
        ]
        relevance_score = 55

        result = TopicDriftDetector.detect(topic, notes, relevance_score)

        assert result["detected"] is True
        assert result["severity"] == "medium"

    def test_drift_with_vague_notes(self):
        """Vague language should trigger low severity drift."""
        topic = "Algorithms"
        notes = [
            "Learned some stuff about algorithms",
            "It was basically about things and whatever",
            "Pretty much understood etc"
        ]
        relevance_score = 70  # Good relevance but vague notes

        result = TopicDriftDetector.detect(topic, notes, relevance_score)

        assert result["detected"] is True
        assert result["severity"] == "low"
        assert "vague" in result["details"].lower()

    def test_drift_with_empty_notes(self):
        """Empty notes should trigger high severity drift."""
        topic = "Python"
        notes = []
        relevance_score = 50

        result = TopicDriftDetector.detect(topic, notes, relevance_score)

        assert result["detected"] is True
        assert result["severity"] == "high"
        assert "no notes" in result["details"].lower()

    def test_subject_area_detection(self):
        """Should detect when notes are about a different subject area."""
        topic = "History of Rome"
        notes = [
            "Wrote a function to calculate fibonacci",
            "Used a loop and variable to store results",
            "Debugging the algorithm"
        ]
        relevance_score = 30

        result = TopicDriftDetector.detect(topic, notes, relevance_score)

        assert result["detected"] is True
        # Should detect programming-related content


class TestOverconfidenceDetector:
    """Test cases for overconfidence detection."""

    def test_no_overconfidence_with_active_notes(self):
        """Active learning notes should not trigger overconfidence."""
        topic = "Recursion"
        notes = [
            "Learned that recursion needs a base case because otherwise it loops forever",
            "Practiced solving factorial - realized the pattern",
            "Therefore, every recursive function needs termination condition"
        ]
        actual_minutes = 25
        planned_minutes = 25

        result = OverconfidenceDetector.detect(topic, notes, actual_minutes, planned_minutes)

        assert result["detected"] is False
        assert result["confidence_gap"] == 0.0

    def test_overconfidence_with_passive_notes(self):
        """Passive consumption notes should trigger overconfidence."""
        topic = "Neural Networks"
        notes = [
            "Watched the 3Blue1Brown video",
            "Saw the explanation of backpropagation",
            "Read about gradient descent"
        ]
        actual_minutes = 45
        planned_minutes = 45

        result = OverconfidenceDetector.detect(topic, notes, actual_minutes, planned_minutes)

        assert result["detected"] is True
        assert result["confidence_gap"] > 0
        assert "watched" in result["details"].lower() or "passive" in result["details"].lower()

    def test_overconfidence_with_sparse_notes(self):
        """Long session with minimal notes should trigger overconfidence."""
        topic = "Database Design"
        notes = [
            "SQL stuff",
            "Tables"
        ]
        actual_minutes = 45
        planned_minutes = 45

        result = OverconfidenceDetector.detect(topic, notes, actual_minutes, planned_minutes)

        assert result["detected"] is True
        assert "minimal notes" in result["details"].lower() or "brief" in result["details"].lower()

    def test_overconfidence_with_empty_notes(self):
        """No notes should definitely trigger overconfidence."""
        topic = "Anything"
        notes = []
        actual_minutes = 30
        planned_minutes = 30

        result = OverconfidenceDetector.detect(topic, notes, actual_minutes, planned_minutes)

        assert result["detected"] is True
        assert result["confidence_gap"] == 1.0
        assert "no notes" in result["details"].lower()

    def test_no_overconfidence_short_session(self):
        """Short session with brief notes is acceptable."""
        topic = "Quick Review"
        notes = [
            "Reviewed key points",
            "Checked understanding"
        ]
        actual_minutes = 10
        planned_minutes = 15

        result = OverconfidenceDetector.detect(topic, notes, actual_minutes, planned_minutes)

        # Short session shouldn't be flagged for sparse notes
        assert result["confidence_gap"] < 0.6

    def test_mixed_passive_active_notes(self):
        """Mixed passive/active should trigger mild warning or none."""
        topic = "Web Development"
        notes = [
            "Watched tutorial on React hooks and understood the concept",
            "Learned that useState manages component state because it persists across renders",
            "Read documentation about useEffect and realized it handles side effects"
        ]
        actual_minutes = 20  # Shorter session with good notes
        planned_minutes = 20

        result = OverconfidenceDetector.detect(topic, notes, actual_minutes, planned_minutes)

        # Has both passive and active, should be mild or no warning
        # The algorithm checks passive > active, so mixed should have lower gap
        assert result["confidence_gap"] <= 0.7


class TestDetectorEdgeCases:
    """Edge cases and boundary conditions."""

    def test_drift_with_single_word_topic(self):
        """Single word topic should work."""
        result = TopicDriftDetector.detect(
            "Python",
            ["Learned about Python lists"],
            75
        )
        assert isinstance(result["detected"], bool)

    def test_drift_with_long_topic(self):
        """Long topic name should work."""
        result = TopicDriftDetector.detect(
            "Introduction to Machine Learning and Artificial Intelligence Fundamentals",
            ["Covered ML basics"],
            60
        )
        assert isinstance(result["detected"], bool)

    def test_overconfidence_with_zero_minutes(self):
        """Zero actual minutes should handle gracefully."""
        result = OverconfidenceDetector.detect(
            "Test",
            ["Some note"],
            0,
            25
        )
        assert isinstance(result["detected"], bool)

    def test_detectors_return_required_fields(self):
        """Verify all required fields are present."""
        drift_result = TopicDriftDetector.detect("Topic", ["Note"], 50)
        assert "detected" in drift_result
        assert "details" in drift_result
        assert "severity" in drift_result

        overconf_result = OverconfidenceDetector.detect("Topic", ["Note"], 25, 25)
        assert "detected" in overconf_result
        assert "details" in overconf_result
        assert "confidence_gap" in overconf_result
