#!/usr/bin/env python3
"""
Smart Study & Focus Companion (AI-Assisted)
============================================
Complete Study Tracker with Intelligent Feedback

Phase 1: Core Features
- Set study topic and planned duration
- Track actual study time and breaks
- Post-session note taking (3-5 bullets)
- AI-powered: summarization, topic relevance, focus feedback

Phase 2: AI Value
- Topic drift detection (notes don't match topic)
- Overconfidence detection (watched but didn't retain)
- Revision task suggestions
- Next session planning

Phase 3: Weekly Reports
- Study time vs retention analysis
- Topics with low understanding
- CLI visualizations (charts, trends)
- Actionable weekly recommendations
"""

import json
import time
import os
import re
import sys
import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict
import textwrap
import math

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SESSIONS_FILE = DATA_DIR / "sessions.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Break:
    """Represents a break taken during study."""
    start_time: str
    end_time: str
    duration_seconds: int


@dataclass
class StudySession:
    """Complete study session data."""
    id: str
    topic: str
    planned_minutes: int
    actual_minutes: float
    start_time: str
    end_time: str
    breaks: List[dict]
    total_break_time: int
    notes: List[str]
    # Phase 1: Basic AI feedback
    ai_summary: str
    topic_relevance_score: float
    focus_feedback: str
    completed: bool
    # Phase 2: Advanced detection
    topic_drift_detected: bool = False
    drift_details: str = ""
    overconfidence_detected: bool = False
    overconfidence_details: str = ""
    revision_tasks: List[str] = None
    next_session_plan: str = ""

    def __post_init__(self):
        if self.revision_tasks is None:
            self.revision_tasks = []

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StudySession":
        # Handle missing Phase 2 fields for backward compatibility
        defaults = {
            "topic_drift_detected": False,
            "drift_details": "",
            "overconfidence_detected": False,
            "overconfidence_details": "",
            "revision_tasks": [],
            "next_session_plan": ""
        }
        for key, default in defaults.items():
            if key not in data:
                data[key] = default
        return cls(**data)


# ============================================================================
# DATA PERSISTENCE
# ============================================================================

def load_sessions() -> List[StudySession]:
    """Load all sessions from file."""
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [StudySession.from_dict(s) for s in data.get("sessions", [])]
    return []


def save_session(session: StudySession) -> None:
    """Save a session to file."""
    sessions = []
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            sessions = data.get("sessions", [])

    sessions.append(session.to_dict())

    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({"sessions": sessions}, f, indent=2, ensure_ascii=False)


# ============================================================================
# PHASE 2: DETECTION ENGINES
# ============================================================================

class TopicDriftDetector:
    """
    Detects when notes don't match the stated study topic.
    Uses keyword analysis and semantic indicators.
    """

    # Common topic keywords by subject area
    SUBJECT_KEYWORDS = {
        "math": ["equation", "formula", "calculate", "solve", "proof", "theorem",
                 "derivative", "integral", "function", "variable", "graph"],
        "programming": ["code", "function", "class", "variable", "loop", "algorithm",
                       "debug", "compile", "syntax", "api", "method", "object"],
        "science": ["experiment", "hypothesis", "theory", "data", "observation",
                   "molecule", "reaction", "cell", "energy", "force"],
        "history": ["century", "war", "civilization", "period", "revolution",
                   "empire", "dynasty", "treaty", "movement", "era"],
        "language": ["grammar", "vocabulary", "sentence", "verb", "noun",
                    "pronunciation", "conjugation", "tense", "phrase"],
    }

    @classmethod
    def detect(cls, topic: str, notes: List[str], relevance_score: float) -> dict:
        """
        Detect topic drift.
        Returns: {detected: bool, details: str, severity: str}
        """
        if not notes:
            return {
                "detected": True,
                "details": "No notes taken. Cannot verify topic engagement.",
                "severity": "high"
            }

        notes_text = " ".join(notes).lower()
        topic_lower = topic.lower()

        # Check 1: Direct topic mention
        topic_words = set(topic_lower.split()) - {"the", "a", "an", "and", "or", "of", "in", "to"}
        topic_mentions = sum(1 for w in topic_words if w in notes_text)
        topic_mention_ratio = topic_mentions / len(topic_words) if topic_words else 0

        # Check 2: Subject area alignment
        detected_subjects = []
        for subject, keywords in cls.SUBJECT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in notes_text)
            if matches >= 2:
                detected_subjects.append((subject, matches))

        # Check 3: Note specificity (vague notes = possible drift)
        vague_indicators = ["stuff", "things", "something", "whatever", "etc",
                           "and more", "basically", "pretty much", "kind of"]
        vague_count = sum(1 for v in vague_indicators if v in notes_text)

        # Decision logic
        drift_detected = False
        details = ""
        severity = "none"

        if relevance_score < 40:
            drift_detected = True
            severity = "high"
            details = f"Your notes show low relevance ({relevance_score:.0f}%) to '{topic}'. "

            if detected_subjects and not any(topic_lower in s[0] for s in detected_subjects):
                top_subject = max(detected_subjects, key=lambda x: x[1])[0]
                details += f"Notes seem more related to {top_subject}. "

            details += "Did you switch topics during the session?"

        elif relevance_score < 60:
            drift_detected = True
            severity = "medium"
            details = f"Partial topic drift detected. Your notes partially cover '{topic}' "
            details += "but may be missing key concepts or wandering into tangents."

        elif vague_count >= 2:
            drift_detected = True
            severity = "low"
            details = "Notes are vague. Try to include specific terms and concepts "
            details += f"related to '{topic}' for better retention."

        return {
            "detected": drift_detected,
            "details": details,
            "severity": severity
        }


class OverconfidenceDetector:
    """
    Detects signs that user may have watched/read without retaining.
    Analyzes note quality vs session length.
    """

    # Patterns suggesting passive consumption
    PASSIVE_PATTERNS = [
        "watched", "saw", "video", "lecture", "tutorial",
        "read", "reading", "article", "chapter", "book"
    ]

    # Patterns suggesting active learning
    ACTIVE_PATTERNS = [
        "learned", "understand", "realized", "discovered",
        "practiced", "solved", "implemented", "applied",
        "because", "therefore", "means that", "so that",
        "example", "such as", "specifically"
    ]

    @classmethod
    def detect(cls, topic: str, notes: List[str],
               actual_minutes: float, planned_minutes: int) -> dict:
        """
        Detect overconfidence (consumption without retention).
        Returns: {detected: bool, details: str, confidence_gap: float}
        """
        if not notes:
            return {
                "detected": True,
                "details": "No notes taken after studying. High risk of zero retention.",
                "confidence_gap": 1.0
            }

        notes_text = " ".join(notes).lower()
        avg_note_length = sum(len(n.split()) for n in notes) / len(notes)
        total_words = sum(len(n.split()) for n in notes)

        # Check 1: Passive vs Active language ratio
        passive_count = sum(1 for p in cls.PASSIVE_PATTERNS if p in notes_text)
        active_count = sum(1 for a in cls.ACTIVE_PATTERNS if a in notes_text)

        # Check 2: Note depth vs time spent
        # Heuristic: ~5-10 meaningful words per 5 minutes of study is healthy
        expected_min_words = (actual_minutes / 5) * 5
        word_deficit = max(0, expected_min_words - total_words)

        # Check 3: Session completion with minimal notes
        long_session = actual_minutes >= 30
        sparse_notes = len(notes) < 3 or avg_note_length < 6

        # Decision logic
        detected = False
        details = ""
        confidence_gap = 0.0

        # High confidence gap indicators
        if passive_count > 0 and active_count == 0:
            detected = True
            confidence_gap = 0.7
            details = "Your notes describe what you watched/read, not what you learned. "
            details += "Try explaining concepts in your own words."

        elif long_session and sparse_notes:
            detected = True
            confidence_gap = 0.6
            details = f"You studied for {actual_minutes:.0f} minutes but captured minimal notes. "
            details += "This suggests passive consumption. What can you recall without looking?"

        elif word_deficit > 15:
            detected = True
            confidence_gap = 0.5
            details = f"Your notes are brief relative to study time. "
            details += "Challenge: Can you explain the key points to someone else?"

        elif passive_count > active_count and len(notes) >= 3:
            detected = True
            confidence_gap = 0.3
            details = "Notes lean toward describing content rather than insights. "
            details += "Add 'because' and 'therefore' to deepen understanding."

        return {
            "detected": detected,
            "details": details,
            "confidence_gap": confidence_gap
        }


class RevisionTaskGenerator:
    """
    Generates actionable revision tasks based on session analysis.
    """

    @classmethod
    def generate(cls, topic: str, notes: List[str],
                 drift_detected: bool, overconfidence_detected: bool,
                 relevance_score: float) -> List[str]:
        """Generate 2-4 specific revision tasks."""
        tasks = []

        # Task 1: Based on topic drift
        if drift_detected and relevance_score < 50:
            tasks.append(f"Re-study '{topic}' with a specific question in mind")
            tasks.append("Write a one-paragraph summary of the core concept")

        # Task 2: Based on overconfidence
        if overconfidence_detected:
            tasks.append("Close all materials and write what you remember")
            tasks.append("Teach the concept to an imaginary student (out loud)")

        # Task 3: Based on note quality
        if notes:
            # Find the shortest note - likely needs expansion
            shortest = min(notes, key=lambda n: len(n.split()))
            if len(shortest.split()) < 8:
                tasks.append(f"Expand on: '{shortest[:50]}...' - add examples")

        # Task 4: Active recall
        if relevance_score >= 60:
            tasks.append(f"Tomorrow: Quiz yourself on 3 key points from '{topic}'")

        # Task 5: Connection building
        if len(notes) >= 3:
            tasks.append("Create a simple diagram connecting the main concepts")

        # Limit to 4 tasks
        return tasks[:4] if tasks else ["Review your notes and add one new insight"]

    @classmethod
    def generate_with_claude(cls, topic: str, notes: List[str],
                            drift_info: dict, overconfidence_info: dict) -> List[str]:
        """Use Claude to generate more intelligent revision tasks."""
        if not ANTHROPIC_API_KEY:
            return cls.generate(
                topic, notes,
                drift_info.get("detected", False),
                overconfidence_info.get("detected", False),
                50  # default relevance
            )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

            notes_text = "\n".join(f"- {note}" for note in notes)

            prompt = f"""Based on this study session, generate 3-4 specific revision tasks.

TOPIC: {topic}

STUDENT'S NOTES:
{notes_text}

ISSUES DETECTED:
- Topic drift: {drift_info.get('details', 'None')}
- Overconfidence: {overconfidence_info.get('details', 'None')}

Generate 3-4 SHORT, SPECIFIC revision tasks that will help this student actually learn the material.
Tasks should be actionable (start with a verb) and completable in 5-15 minutes each.

Respond as a JSON array of strings:
["task 1", "task 2", "task 3"]"""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())[:4]

        except Exception:
            pass

        return cls.generate(topic, notes, drift_info.get("detected", False),
                          overconfidence_info.get("detected", False), 50)


class NextSessionPlanner:
    """
    Suggests what to do in the next study session.
    """

    @classmethod
    def plan(cls, current_session: dict, all_sessions: List[StudySession]) -> str:
        """Generate next session recommendation."""
        topic = current_session.get("topic", "")
        relevance = current_session.get("relevance_score", 50)
        drift = current_session.get("drift_detected", False)
        overconfidence = current_session.get("overconfidence_detected", False)
        actual_mins = current_session.get("actual_minutes", 0)

        # Check topic history
        topic_sessions = [s for s in all_sessions
                         if topic.lower() in s.topic.lower()]
        times_studied = len(topic_sessions)

        # Decision logic
        if drift or relevance < 50:
            return (f"Restart '{topic}' with focused 15-min session. "
                   f"Set a specific question to answer before starting.")

        elif overconfidence:
            return (f"Begin with a 5-min recall test on '{topic}' (no notes). "
                   f"Then fill gaps with targeted review.")

        elif times_studied >= 3 and relevance >= 70:
            return (f"You've studied '{topic}' {times_studied} times. "
                   f"Try practice problems or teach the concept to solidify.")

        elif actual_mins < 20 and relevance >= 60:
            return (f"Good start on '{topic}'. Next: extend to 25-30 min "
                   f"and go deeper into one subtopic.")

        elif relevance >= 80:
            return (f"Strong session! Next: connect '{topic}' to related concepts "
                   f"or apply it to a real problem.")

        else:
            return (f"Continue with '{topic}'. Focus on understanding 'why' "
                   f"not just 'what'. Add more examples to your notes.")


# ============================================================================
# AI ENGINE (Phase 1 + Phase 2)
# ============================================================================

class AIEngine:
    """
    AI-powered analysis with Phase 1 basics and Phase 2 detection.
    """

    @classmethod
    def full_analysis(cls, topic: str, notes: List[str],
                     planned_mins: int, actual_mins: float,
                     break_count: int, total_break_secs: int,
                     all_sessions: List[StudySession]) -> dict:
        """
        Complete analysis including Phase 1 + Phase 2 features.
        """
        # Phase 1: Basic analysis
        basic = cls._analyze_basic(
            topic, notes, planned_mins, actual_mins,
            break_count, total_break_secs
        )

        # Phase 2: Detection
        drift_info = TopicDriftDetector.detect(
            topic, notes, basic["topic_relevance"]
        )

        overconfidence_info = OverconfidenceDetector.detect(
            topic, notes, actual_mins, planned_mins
        )

        # Phase 2: Revision tasks
        revision_tasks = RevisionTaskGenerator.generate_with_claude(
            topic, notes, drift_info, overconfidence_info
        ) if ANTHROPIC_API_KEY else RevisionTaskGenerator.generate(
            topic, notes, drift_info["detected"],
            overconfidence_info["detected"], basic["topic_relevance"]
        )

        # Phase 2: Next session plan
        next_plan = NextSessionPlanner.plan({
            "topic": topic,
            "relevance_score": basic["topic_relevance"],
            "drift_detected": drift_info["detected"],
            "overconfidence_detected": overconfidence_info["detected"],
            "actual_minutes": actual_mins
        }, all_sessions)

        return {
            # Phase 1
            "summary": basic["summary"],
            "topic_relevance": basic["topic_relevance"],
            "focus_feedback": basic["focus_feedback"],
            # Phase 2
            "topic_drift_detected": drift_info["detected"],
            "drift_details": drift_info["details"],
            "overconfidence_detected": overconfidence_info["detected"],
            "overconfidence_details": overconfidence_info["details"],
            "revision_tasks": revision_tasks,
            "next_session_plan": next_plan
        }

    @classmethod
    def _analyze_basic(cls, topic: str, notes: List[str],
                      planned_mins: int, actual_mins: float,
                      break_count: int, total_break_secs: int) -> dict:
        """Phase 1 basic analysis."""

        if ANTHROPIC_API_KEY:
            return cls._analyze_with_claude(
                topic, notes, planned_mins, actual_mins,
                break_count, total_break_secs
            )
        else:
            return cls._analyze_locally(
                topic, notes, planned_mins, actual_mins,
                break_count, total_break_secs
            )

    @classmethod
    def _analyze_with_claude(cls, topic: str, notes: List[str],
                            planned_mins: int, actual_mins: float,
                            break_count: int, total_break_secs: int) -> dict:
        """Use Claude API for basic analysis."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

            notes_text = "\n".join(f"- {note}" for note in notes)

            prompt = f"""Analyze this study session briefly.

TOPIC: {topic}
NOTES:
{notes_text}
STATS: {actual_mins:.0f}/{planned_mins} min, {break_count} breaks

Provide:
1. SUMMARY (2 sentences): What did they learn?
2. TOPIC_RELEVANCE (0-100): How well do notes match the topic?
3. FOCUS_FEEDBACK (2 sentences): Constructive feedback.

JSON format:
{{"summary": "...", "topic_relevance": <number>, "focus_feedback": "..."}}"""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "summary": result.get("summary", ""),
                    "topic_relevance": float(result.get("topic_relevance", 50)),
                    "focus_feedback": result.get("focus_feedback", "")
                }

        except Exception as e:
            print(f"\n  ⚠️  API error: {e}")

        return cls._analyze_locally(topic, notes, planned_mins, actual_mins,
                                   break_count, total_break_secs)

    @classmethod
    def _analyze_locally(cls, topic: str, notes: List[str],
                        planned_mins: int, actual_mins: float,
                        break_count: int, total_break_secs: int) -> dict:
        """Local rule-based analysis."""

        # Summary
        if notes:
            summary_parts = [" ".join(n.split()[:12]) for n in notes[:3]]
            summary = "Covered: " + "; ".join(summary_parts) + "."
        else:
            summary = "No notes recorded."

        # Topic relevance
        topic_words = set(topic.lower().split()) - {"the", "a", "an", "and", "or", "to", "of"}
        notes_text = " ".join(notes).lower()

        if topic_words:
            matches = sum(1 for w in topic_words if w in notes_text)
            base = (matches / len(topic_words)) * 100
        else:
            base = 50

        avg_len = sum(len(n.split()) for n in notes) / len(notes) if notes else 0
        topic_relevance = min(100, base + min(20, avg_len))

        # Focus feedback
        completion = actual_mins / planned_mins if planned_mins > 0 else 0
        feedback = []

        if completion >= 0.95:
            feedback.append("Great time management!")
        elif completion >= 0.7:
            feedback.append(f"Completed {completion*100:.0f}% of planned time.")
        else:
            feedback.append("Consider shorter initial goals.")

        if len(notes) >= 3:
            feedback.append("Good note-taking effort.")
        else:
            feedback.append("Try capturing more key points.")

        return {
            "summary": summary,
            "topic_relevance": round(topic_relevance, 1),
            "focus_feedback": " ".join(feedback)
        }


# ============================================================================
# TIMER WITH BREAK TRACKING
# ============================================================================

class StudyTimer:
    """Focus timer with break tracking."""

    def __init__(self, duration_minutes: int):
        self.duration_seconds = duration_minutes * 60
        self.remaining = self.duration_seconds
        self.breaks: List[Break] = []
        self.is_paused = False
        self.current_break_start = None

    def run(self) -> tuple[float, List[dict], bool]:
        start_time = time.time()

        print("\n" + "═" * 50)
        print("  🎯 FOCUS SESSION STARTED")
        print("═" * 50)
        print("\n  [b] Break  [r] Resume  [q] Quit")
        print("─" * 50)

        get_key = self._setup_key_detection()

        while self.remaining > 0:
            if not self.is_paused:
                self._display_timer()
                time.sleep(1)
                self.remaining -= 1
            else:
                self._display_break()
                time.sleep(0.5)

            key = get_key()
            self._handle_key(key)

            if key == 'q':
                break

        end_time = time.time()
        total_break_secs = sum(b.duration_seconds for b in self.breaks)
        actual_study_secs = (end_time - start_time) - total_break_secs
        completed = self.remaining <= 0

        print("\n\n  " + ("✅ Complete!" if completed else "⏹️ Ended early"))

        return actual_study_secs / 60, [asdict(b) for b in self.breaks], completed

    def _setup_key_detection(self):
        try:
            import msvcrt
            def get_key():
                if msvcrt.kbhit():
                    return msvcrt.getch().decode('utf-8', errors='ignore').lower()
                return None
            return get_key
        except ImportError:
            import sys, select
            def get_key():
                if select.select([sys.stdin], [], [], 0)[0]:
                    return sys.stdin.read(1).lower()
                return None
            return get_key

    def _display_timer(self):
        mins, secs = divmod(self.remaining, 60)
        progress = (self.duration_seconds - self.remaining) / self.duration_seconds
        filled = int(30 * progress)
        bar = "█" * filled + "░" * (30 - filled)
        print(f"\r  🔥 [{bar}] {mins:02d}:{secs:02d}  ", end="", flush=True)

    def _display_break(self):
        if self.current_break_start:
            dur = int(time.time() - self.current_break_start)
            mins, secs = divmod(dur, 60)
            print(f"\r  ☕ BREAK: {mins:02d}:{secs:02d} [r]=resume  ", end="", flush=True)

    def _handle_key(self, key):
        if key == 'b' and not self.is_paused:
            self.is_paused = True
            self.current_break_start = time.time()
            print("\n\n  ☕ Break started\n")
        elif key == 'r' and self.is_paused and self.current_break_start:
            duration = int(time.time() - self.current_break_start)
            self.breaks.append(Break(
                datetime.fromtimestamp(self.current_break_start).isoformat(),
                datetime.now().isoformat(),
                duration
            ))
            self.is_paused = False
            self.current_break_start = None
            print(f"\n\n  ▶️ Resumed ({duration//60}m {duration%60}s break)\n")


# ============================================================================
# NOTE TAKING
# ============================================================================

def collect_notes(topic: str) -> List[str]:
    """Collect 3-5 bullet point notes."""
    print("\n" + "═" * 50)
    print("  📝 WHAT DID YOU LEARN?")
    print("═" * 50)
    print(f"\n  Topic: {topic}")
    print("  Write 3-5 points. Type 'done' to finish.\n")

    notes = []
    for i in range(5):
        prompt = f"  {i+1}. " if i < 3 else f"  {i+1}. (optional) "
        note = input(prompt).strip()
        if note.lower() == 'done':
            break
        if note:
            notes.append(note)

    print(f"\n  {'✅' if len(notes) >= 3 else '⚠️'} {len(notes)} notes recorded")
    return notes


# ============================================================================
# SESSION DISPLAY (Phase 1 + Phase 2)
# ============================================================================

def display_analysis(session: StudySession):
    """Display complete AI analysis."""
    print("\n" + "═" * 50)
    print("  🤖 AI ANALYSIS")
    print("═" * 50)

    # Summary
    print("\n  📋 SUMMARY:")
    for line in textwrap.wrap(session.ai_summary, 46):
        print(f"     {line}")

    # Topic Relevance
    print(f"\n  🎯 TOPIC RELEVANCE: {session.topic_relevance_score:.0f}/100")
    if session.topic_relevance_score >= 80:
        print("     ✓ Notes align well with topic")
    elif session.topic_relevance_score >= 60:
        print("     → Could be more specific")
    else:
        print("     ⚠ Notes may be off-topic")

    # Phase 2: Topic Drift Warning
    if session.topic_drift_detected:
        print("\n  ⚠️  TOPIC DRIFT DETECTED:")
        for line in textwrap.wrap(session.drift_details, 44):
            print(f"     {line}")

    # Phase 2: Overconfidence Warning
    if session.overconfidence_detected:
        print("\n  ⚠️  OVERCONFIDENCE WARNING:")
        for line in textwrap.wrap(session.overconfidence_details, 44):
            print(f"     {line}")

    # Focus Feedback
    print("\n  💡 FOCUS FEEDBACK:")
    for line in textwrap.wrap(session.focus_feedback, 46):
        print(f"     {line}")

    # Stats
    print("\n" + "─" * 50)
    print("  📊 SESSION STATS:")
    print(f"     • Planned: {session.planned_minutes} min")
    print(f"     • Actual: {session.actual_minutes:.1f} min")
    print(f"     • Breaks: {len(session.breaks)}")
    completion = (session.actual_minutes / session.planned_minutes * 100) if session.planned_minutes > 0 else 0
    print(f"     • Completion: {completion:.0f}%")

    # Phase 2: Revision Tasks
    if session.revision_tasks:
        print("\n" + "═" * 50)
        print("  📝 REVISION TASKS")
        print("═" * 50)
        for i, task in enumerate(session.revision_tasks, 1):
            print(f"\n  {i}. {task}")

    # Phase 2: Next Session Plan
    if session.next_session_plan:
        print("\n" + "═" * 50)
        print("  📅 NEXT SESSION")
        print("═" * 50)
        for line in textwrap.wrap(session.next_session_plan, 46):
            print(f"\n     {line}")


def display_history():
    """Display session history."""
    sessions = load_sessions()

    print("\n" + "═" * 50)
    print("  📜 SESSION HISTORY")
    print("═" * 50)

    if not sessions:
        print("\n  No sessions yet!")
        return

    recent = sessions[-10:][::-1]

    print(f"\n  {'Date':<12} {'Topic':<18} {'Min':<6} {'Rel':<6} {'Issues'}")
    print("  " + "-" * 48)

    for s in recent:
        date = s.start_time[:10]
        topic = (s.topic[:16] + "..") if len(s.topic) > 18 else s.topic
        mins = f"{s.actual_minutes:.0f}"
        rel = f"{s.topic_relevance_score:.0f}"
        issues = []
        if s.topic_drift_detected:
            issues.append("drift")
        if s.overconfidence_detected:
            issues.append("overconf")
        issues_str = ",".join(issues) if issues else "✓"
        print(f"  {date:<12} {topic:<18} {mins:<6} {rel:<6} {issues_str}")

    total = sum(s.actual_minutes for s in sessions)
    print(f"\n  Total: {total:.0f} min ({total/60:.1f} hrs) across {len(sessions)} sessions")


# ============================================================================
# PHASE 3: WEEKLY REPORT & VISUALIZATION
# ============================================================================

class CLIChart:
    """Simple CLI-based charts and visualizations."""

    @staticmethod
    def horizontal_bar(label: str, value: float, max_value: float,
                       width: int = 20, fill: str = "█", empty: str = "░") -> str:
        """Create a horizontal bar chart line."""
        if max_value <= 0:
            filled = 0
        else:
            filled = int((value / max_value) * width)
        bar = fill * filled + empty * (width - filled)
        return f"  {label:<12} [{bar}] {value:.0f}"

    @staticmethod
    def sparkline(values: List[float], width: int = 7) -> str:
        """Create a mini sparkline from values."""
        if not values:
            return "─" * width

        chars = " ▁▂▃▄▅▆▇█"
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        result = ""
        for v in values[-width:]:
            idx = int(((v - min_val) / range_val) * (len(chars) - 1))
            result += chars[idx]

        return result

    @staticmethod
    def trend_arrow(current: float, previous: float) -> str:
        """Get trend arrow based on change."""
        if previous == 0:
            return "→"
        change = ((current - previous) / previous) * 100
        if change > 10:
            return "↑"
        elif change < -10:
            return "↓"
        return "→"


class WeeklyReportGenerator:
    """Generates comprehensive weekly study reports."""

    @classmethod
    def generate(cls, sessions: List[StudySession]) -> dict:
        """Generate complete weekly report data."""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)

        # Filter sessions for this week and last week
        this_week = []
        last_week = []

        for s in sessions:
            session_date = datetime.fromisoformat(s.start_time).date()
            if week_start <= session_date <= week_end:
                this_week.append(s)
            elif week_start - timedelta(days=7) <= session_date < week_start:
                last_week.append(s)

        return {
            "period": {
                "start": week_start.isoformat(),
                "end": week_end.isoformat()
            },
            "overview": cls._calculate_overview(this_week, last_week),
            "daily_breakdown": cls._daily_breakdown(this_week, week_start),
            "topic_analysis": cls._topic_analysis(this_week),
            "time_vs_retention": cls._time_vs_retention(this_week),
            "problem_areas": cls._identify_problem_areas(this_week),
            "recommendations": cls._generate_recommendations(this_week, last_week),
            "streak": cls._calculate_streak(sessions)
        }

    @classmethod
    def _calculate_overview(cls, this_week: List[StudySession],
                           last_week: List[StudySession]) -> dict:
        """Calculate overview statistics."""
        def stats(sessions):
            if not sessions:
                return {"time": 0, "sessions": 0, "avg_relevance": 0, "issues": 0}
            return {
                "time": sum(s.actual_minutes for s in sessions),
                "sessions": len(sessions),
                "avg_relevance": sum(s.topic_relevance_score for s in sessions) / len(sessions),
                "issues": sum(1 for s in sessions if s.topic_drift_detected or s.overconfidence_detected)
            }

        this_stats = stats(this_week)
        last_stats = stats(last_week)

        return {
            "this_week": this_stats,
            "last_week": last_stats,
            "time_change": this_stats["time"] - last_stats["time"],
            "sessions_change": this_stats["sessions"] - last_stats["sessions"]
        }

    @classmethod
    def _daily_breakdown(cls, sessions: List[StudySession],
                        week_start: datetime.date) -> List[dict]:
        """Break down study time by day."""
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        daily = {i: {"day": days[i], "minutes": 0, "sessions": 0, "avg_score": []}
                for i in range(7)}

        for s in sessions:
            day_idx = datetime.fromisoformat(s.start_time).weekday()
            daily[day_idx]["minutes"] += s.actual_minutes
            daily[day_idx]["sessions"] += 1
            daily[day_idx]["avg_score"].append(s.topic_relevance_score)

        # Calculate averages
        for d in daily.values():
            d["avg_score"] = sum(d["avg_score"]) / len(d["avg_score"]) if d["avg_score"] else 0

        return list(daily.values())

    @classmethod
    def _topic_analysis(cls, sessions: List[StudySession]) -> List[dict]:
        """Analyze performance by topic."""
        topics = defaultdict(lambda: {
            "time": 0, "sessions": 0, "scores": [], "issues": 0
        })

        for s in sessions:
            t = topics[s.topic]
            t["time"] += s.actual_minutes
            t["sessions"] += 1
            t["scores"].append(s.topic_relevance_score)
            if s.topic_drift_detected or s.overconfidence_detected:
                t["issues"] += 1

        result = []
        for topic, data in topics.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            result.append({
                "topic": topic,
                "time": data["time"],
                "sessions": data["sessions"],
                "avg_score": avg_score,
                "issues": data["issues"],
                "understanding": "good" if avg_score >= 70 else "medium" if avg_score >= 50 else "low"
            })

        return sorted(result, key=lambda x: x["time"], reverse=True)

    @classmethod
    def _time_vs_retention(cls, sessions: List[StudySession]) -> dict:
        """Analyze relationship between study time and retention."""
        if not sessions:
            return {"correlation": "insufficient_data", "insight": "Need more sessions"}

        # Group by time buckets
        short = [s for s in sessions if s.actual_minutes < 20]
        medium = [s for s in sessions if 20 <= s.actual_minutes < 40]
        long = [s for s in sessions if s.actual_minutes >= 40]

        def avg_score(session_list):
            if not session_list:
                return 0
            return sum(s.topic_relevance_score for s in session_list) / len(session_list)

        return {
            "short_sessions": {"count": len(short), "avg_score": avg_score(short)},
            "medium_sessions": {"count": len(medium), "avg_score": avg_score(medium)},
            "long_sessions": {"count": len(long), "avg_score": avg_score(long)},
            "optimal_duration": cls._find_optimal_duration(sessions)
        }

    @classmethod
    def _find_optimal_duration(cls, sessions: List[StudySession]) -> str:
        """Find the optimal session duration based on scores."""
        if len(sessions) < 3:
            return "Need more data"

        # Find duration with highest average score
        duration_scores = defaultdict(list)
        for s in sessions:
            bucket = (int(s.actual_minutes) // 10) * 10
            duration_scores[bucket].append(s.topic_relevance_score)

        best_bucket = 25
        best_score = 0
        for bucket, scores in duration_scores.items():
            if len(scores) >= 2:
                avg = sum(scores) / len(scores)
                if avg > best_score:
                    best_score = avg
                    best_bucket = bucket

        return f"{best_bucket}-{best_bucket + 10} minutes"

    @classmethod
    def _identify_problem_areas(cls, sessions: List[StudySession]) -> List[dict]:
        """Identify topics/patterns that need attention."""
        problems = []

        # Group by topic
        topic_data = defaultdict(list)
        for s in sessions:
            topic_data[s.topic].append(s)

        for topic, topic_sessions in topic_data.items():
            issues = []

            # Low average score
            avg_score = sum(s.topic_relevance_score for s in topic_sessions) / len(topic_sessions)
            if avg_score < 60:
                issues.append(f"Low understanding ({avg_score:.0f}%)")

            # High drift rate
            drift_rate = sum(1 for s in topic_sessions if s.topic_drift_detected) / len(topic_sessions)
            if drift_rate > 0.5:
                issues.append(f"Frequent topic drift ({drift_rate*100:.0f}%)")

            # Overconfidence pattern
            overconf_rate = sum(1 for s in topic_sessions if s.overconfidence_detected) / len(topic_sessions)
            if overconf_rate > 0.5:
                issues.append(f"Retention issues ({overconf_rate*100:.0f}%)")

            if issues:
                problems.append({
                    "topic": topic,
                    "sessions": len(topic_sessions),
                    "issues": issues,
                    "priority": "high" if len(issues) >= 2 else "medium"
                })

        return sorted(problems, key=lambda x: len(x["issues"]), reverse=True)

    @classmethod
    def _generate_recommendations(cls, this_week: List[StudySession],
                                  last_week: List[StudySession]) -> List[str]:
        """Generate actionable weekly recommendations."""
        recommendations = []

        if not this_week:
            return ["Start tracking your study sessions to get personalized recommendations!"]

        this_time = sum(s.actual_minutes for s in this_week)
        last_time = sum(s.actual_minutes for s in last_week) if last_week else 0

        # Time-based recommendations
        if this_time < 120:  # Less than 2 hours
            recommendations.append(
                "⏰ Study time is low this week. Try scheduling 2-3 focused sessions."
            )
        elif this_time > last_time * 1.5 and last_time > 0:
            recommendations.append(
                "📈 Great increase in study time! Make sure to include breaks to avoid burnout."
            )

        # Quality-based recommendations
        avg_score = sum(s.topic_relevance_score for s in this_week) / len(this_week)
        if avg_score < 60:
            recommendations.append(
                "🎯 Focus quality is low. Try the Pomodoro technique (25 min focused + 5 min break)."
            )

        # Issue-based recommendations
        drift_count = sum(1 for s in this_week if s.topic_drift_detected)
        if drift_count > len(this_week) * 0.3:
            recommendations.append(
                "📍 Topic drift detected often. Write your learning goal before each session."
            )

        overconf_count = sum(1 for s in this_week if s.overconfidence_detected)
        if overconf_count > len(this_week) * 0.3:
            recommendations.append(
                "💭 Passive learning detected. Add more 'why' and 'how' to your notes."
            )

        # Topic variety
        topics = set(s.topic for s in this_week)
        if len(topics) == 1 and len(this_week) > 3:
            recommendations.append(
                "📚 Consider varying your topics. Interleaved practice improves retention."
            )

        return recommendations[:4] if recommendations else ["Keep up the good work! 🌟"]

    @classmethod
    def _calculate_streak(cls, all_sessions: List[StudySession]) -> dict:
        """Calculate current and longest study streak."""
        if not all_sessions:
            return {"current": 0, "longest": 0}

        dates = sorted(set(
            datetime.fromisoformat(s.start_time).date()
            for s in all_sessions
        ))

        if not dates:
            return {"current": 0, "longest": 0}

        streaks = []
        current = 1

        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                current += 1
            else:
                streaks.append(current)
                current = 1
        streaks.append(current)

        # Check if streak is still active
        today = datetime.now().date()
        last_study = dates[-1]
        active = (today - last_study).days <= 1

        return {
            "current": current if active else 0,
            "longest": max(streaks),
            "last_study": last_study.isoformat()
        }


def display_weekly_report():
    """Display the weekly report with visualizations."""
    sessions = load_sessions()

    print("\n" + "═" * 50)
    print("  📊 WEEKLY STUDY REPORT")
    print("═" * 50)

    if not sessions:
        print("\n  No sessions recorded yet!")
        print("  Complete some study sessions to see your weekly report.")
        return

    report = WeeklyReportGenerator.generate(sessions)
    overview = report["overview"]
    this_week = overview["this_week"]
    last_week = overview["last_week"]

    # Period
    print(f"\n  📅 Week: {report['period']['start']} to {report['period']['end']}")

    # Streak
    streak = report["streak"]
    if streak["current"] > 0:
        print(f"  🔥 Current Streak: {streak['current']} days")
    print(f"  🏆 Longest Streak: {streak['longest']} days")

    # Overview comparison
    print("\n" + "─" * 50)
    print("  📈 THIS WEEK vs LAST WEEK")
    print("─" * 50)

    time_arrow = CLIChart.trend_arrow(this_week["time"], last_week["time"])
    sess_arrow = CLIChart.trend_arrow(this_week["sessions"], last_week["sessions"])

    print(f"\n  Study Time:  {this_week['time']:.0f} min {time_arrow} (was {last_week['time']:.0f})")
    print(f"  Sessions:    {this_week['sessions']} {sess_arrow} (was {last_week['sessions']})")
    print(f"  Avg Score:   {this_week['avg_relevance']:.0f}/100")
    print(f"  Issues:      {this_week['issues']} sessions with focus problems")

    # Daily breakdown chart
    daily = report["daily_breakdown"]
    if any(d["minutes"] > 0 for d in daily):
        print("\n" + "─" * 50)
        print("  📅 DAILY BREAKDOWN")
        print("─" * 50 + "\n")

        max_mins = max(d["minutes"] for d in daily) or 1
        for d in daily:
            bar = CLIChart.horizontal_bar(d["day"], d["minutes"], max_mins, width=15)
            score = f"({d['avg_score']:.0f}%)" if d["sessions"] > 0 else ""
            print(f"{bar} min {score}")

    # Time vs Retention
    tvr = report["time_vs_retention"]
    print("\n" + "─" * 50)
    print("  ⏱️  TIME vs RETENTION")
    print("─" * 50)
    print(f"\n  Short (<20m):  {tvr['short_sessions']['count']} sessions, avg {tvr['short_sessions']['avg_score']:.0f}%")
    print(f"  Medium (20-40m): {tvr['medium_sessions']['count']} sessions, avg {tvr['medium_sessions']['avg_score']:.0f}%")
    print(f"  Long (40m+):   {tvr['long_sessions']['count']} sessions, avg {tvr['long_sessions']['avg_score']:.0f}%")
    print(f"\n  💡 Optimal duration: {tvr['optimal_duration']}")

    # Topic Analysis
    topics = report["topic_analysis"]
    if topics:
        print("\n" + "─" * 50)
        print("  📚 TOPICS STUDIED")
        print("─" * 50)

        max_time = max(t["time"] for t in topics) if topics else 1
        for t in topics[:5]:  # Top 5 topics
            understanding_icon = {"good": "✅", "medium": "➖", "low": "⚠️"}[t["understanding"]]
            bar = CLIChart.horizontal_bar(
                t["topic"][:10],
                t["time"],
                max_time,
                width=12
            )
            print(f"{bar} min {understanding_icon}")

    # Problem Areas
    problems = report["problem_areas"]
    if problems:
        print("\n" + "─" * 50)
        print("  ⚠️  AREAS NEEDING ATTENTION")
        print("─" * 50)

        for p in problems[:3]:
            priority_icon = "🔴" if p["priority"] == "high" else "🟡"
            print(f"\n  {priority_icon} {p['topic']}")
            for issue in p["issues"]:
                print(f"     • {issue}")

    # Recommendations
    recs = report["recommendations"]
    print("\n" + "═" * 50)
    print("  💡 RECOMMENDATIONS")
    print("═" * 50)

    for rec in recs:
        print(f"\n  • {rec}")

    # Weekly grade
    print("\n" + "─" * 50)
    grade = cls_calculate_weekly_grade(this_week)
    print(f"\n  📊 WEEKLY GRADE: {grade['letter']} ({grade['score']}/100)")
    print(f"     {grade['message']}")


def cls_calculate_weekly_grade(stats: dict) -> dict:
    """Calculate an overall weekly grade."""
    score = 0

    # Time component (max 40 points)
    # 5+ hours = 40, 3 hours = 30, 1 hour = 15
    time_score = min(40, (stats["time"] / 300) * 40)
    score += time_score

    # Quality component (max 40 points)
    quality_score = (stats["avg_relevance"] / 100) * 40
    score += quality_score

    # Consistency component (max 20 points)
    # Based on number of sessions (5+ sessions = 20)
    consistency_score = min(20, stats["sessions"] * 4)
    score += consistency_score

    # Penalty for issues
    issue_penalty = stats["issues"] * 5
    score = max(0, score - issue_penalty)

    # Determine grade
    if score >= 90:
        letter, message = "A+", "Outstanding week! Keep this momentum!"
    elif score >= 80:
        letter, message = "A", "Excellent work! You're building strong habits."
    elif score >= 70:
        letter, message = "B", "Good progress. A bit more consistency would help."
    elif score >= 60:
        letter, message = "C", "Decent effort. Try to increase focus quality."
    elif score >= 50:
        letter, message = "D", "Room for improvement. Set smaller, achievable goals."
    else:
        letter, message = "F", "Let's restart fresh. Even 15 min/day makes a difference."

    return {"score": round(score), "letter": letter, "message": message}


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def start_session():
    """Main study session flow."""
    print("\n" + "═" * 50)
    print("  📚 NEW STUDY SESSION")
    print("═" * 50)

    # Topic
    topic = input("\n  What are you studying? ").strip()
    if not topic:
        print("  ⚠️ Topic required.")
        return

    # Duration
    print("\n  Duration: [1] 15m  [2] 25m  [3] 45m  [4] 60m  [5] Custom")
    choice = input("  Select: ").strip()
    durations = {"1": 15, "2": 25, "3": 45, "4": 60}
    if choice == "5":
        try:
            planned_mins = int(input("  Minutes: "))
        except ValueError:
            planned_mins = 25
    else:
        planned_mins = durations.get(choice, 25)

    print(f"\n  ✓ Topic: {topic}")
    print(f"  ✓ Duration: {planned_mins} min")
    input("\n  Press Enter to start...")

    clear_screen()

    # Timer
    timer = StudyTimer(planned_mins)
    start_time = datetime.now()
    actual_mins, breaks, completed = timer.run()
    end_time = datetime.now()
    total_break_time = sum(b["duration_seconds"] for b in breaks)

    # Notes
    notes = collect_notes(topic)

    # Analysis
    print("\n  🔄 Analyzing...")
    all_sessions = load_sessions()

    analysis = AIEngine.full_analysis(
        topic, notes, planned_mins, actual_mins,
        len(breaks), total_break_time, all_sessions
    )

    # Create session
    session = StudySession(
        id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        topic=topic,
        planned_minutes=planned_mins,
        actual_minutes=round(actual_mins, 2),
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        breaks=breaks,
        total_break_time=total_break_time,
        notes=notes,
        ai_summary=analysis["summary"],
        topic_relevance_score=analysis["topic_relevance"],
        focus_feedback=analysis["focus_feedback"],
        completed=completed,
        topic_drift_detected=analysis["topic_drift_detected"],
        drift_details=analysis["drift_details"],
        overconfidence_detected=analysis["overconfidence_detected"],
        overconfidence_details=analysis["overconfidence_details"],
        revision_tasks=analysis["revision_tasks"],
        next_session_plan=analysis["next_session_plan"]
    )

    save_session(session)

    clear_screen()
    display_analysis(session)


def main_menu():
    """Main menu."""
    while True:
        clear_screen()

        print("\n╔" + "═" * 48 + "╗")
        print("║                                                ║")
        print("║   🧠 SMART STUDY & FOCUS COMPANION             ║")
        print("║      AI-Powered Study Tracker                  ║")
        print("║                                                ║")
        print("╚" + "═" * 48 + "╝")

        sessions = load_sessions()
        if sessions:
            today = datetime.now().strftime("%Y-%m-%d")
            today_sessions = [s for s in sessions if s.start_time.startswith(today)]
            today_time = sum(s.actual_minutes for s in today_sessions)
            print(f"\n  📅 Today: {len(today_sessions)} sessions | {today_time:.0f} min")

            # Show streak
            streak_data = WeeklyReportGenerator._calculate_streak(sessions)
            if streak_data["current"] > 0:
                print(f"  🔥 Streak: {streak_data['current']} days")

            # Show if issues detected recently
            recent_issues = sum(1 for s in sessions[-5:]
                              if s.topic_drift_detected or s.overconfidence_detected)
            if recent_issues > 0:
                print(f"  ⚠️  {recent_issues}/5 recent sessions had focus issues")

        api_status = "Claude API ✓" if ANTHROPIC_API_KEY else "Local analysis"
        print(f"  🤖 AI: {api_status}")

        print("\n" + "─" * 50)
        print("\n  [1] 📚 Start Study Session")
        print("  [2] 📊 Weekly Report")
        print("  [3] 📜 View History")
        print("  [4] 🚪 Exit")

        choice = input("\n  Select: ").strip()

        if choice == "1":
            clear_screen()
            start_session()
            input("\n  Press Enter to continue...")
        elif choice == "2":
            clear_screen()
            display_weekly_report()
            input("\n  Press Enter to continue...")
        elif choice == "3":
            clear_screen()
            display_history()
            input("\n  Press Enter to continue...")
        elif choice == "4":
            print("\n  👋 Keep learning!\n")
            break


# ============================================================================
# DEMO MODE - Preloaded sample data for showcasing
# ============================================================================

def generate_demo_sessions() -> List[dict]:
    """Generate realistic demo sessions for showcasing the app."""
    today = datetime.now()
    sessions = []

    # Demo data: varied sessions over the past 2 weeks
    demo_data = [
        # Day -13: Started strong
        {"days_ago": 13, "topic": "Python Basics", "planned": 25, "actual": 24.5,
         "relevance": 85, "notes": ["Learned about list comprehensions", "Practiced slicing syntax",
         "Understood mutable vs immutable types"], "drift": False, "overconf": False},

        # Day -12: Good session
        {"days_ago": 12, "topic": "Python Basics", "planned": 25, "actual": 25,
         "relevance": 78, "notes": ["Dictionaries and their methods", "Learned about .get() for safe access",
         "Practiced nested data structures"], "drift": False, "overconf": False},

        # Day -11: Topic drift example
        {"days_ago": 11, "topic": "Data Structures", "planned": 45, "actual": 40,
         "relevance": 45, "notes": ["Watched video about arrays", "Something about linked lists",
         "Got distracted by YouTube"], "drift": True, "overconf": True},

        # Day -10: Recovery
        {"days_ago": 10, "topic": "Data Structures", "planned": 25, "actual": 25,
         "relevance": 82, "notes": ["Arrays: O(1) access, O(n) insert", "Linked lists: O(n) access, O(1) insert",
         "Trade-offs depend on use case"], "drift": False, "overconf": False},

        # Day -8: New topic
        {"days_ago": 8, "topic": "Algorithms", "planned": 30, "actual": 28,
         "relevance": 75, "notes": ["Binary search requires sorted array", "Time complexity O(log n)",
         "Implemented iterative version"], "drift": False, "overconf": False},

        # Day -7: Passive learning detected
        {"days_ago": 7, "topic": "Machine Learning", "planned": 45, "actual": 45,
         "relevance": 52, "notes": ["Watched 3Blue1Brown neural network video",
         "Saw backpropagation explanation"], "drift": False, "overconf": True},

        # Day -5: Good focus
        {"days_ago": 5, "topic": "Algorithms", "planned": 25, "actual": 25,
         "relevance": 88, "notes": ["Sorting algorithms comparison", "QuickSort: avg O(n log n), worst O(n²)",
         "MergeSort: always O(n log n) but uses extra space"], "drift": False, "overconf": False},

        # Day -4: Short but effective
        {"days_ago": 4, "topic": "Python Basics", "planned": 15, "actual": 15,
         "relevance": 90, "notes": ["Decorators wrap functions", "@property creates getters",
         "functools.wraps preserves metadata"], "drift": False, "overconf": False},

        # Day -3: Struggled
        {"days_ago": 3, "topic": "Machine Learning", "planned": 45, "actual": 30,
         "relevance": 48, "notes": ["Gradient descent moves toward minimum",
         "Learning rate affects convergence"], "drift": True, "overconf": False},

        # Day -2: Good session
        {"days_ago": 2, "topic": "Algorithms", "planned": 25, "actual": 25,
         "relevance": 85, "notes": ["Dynamic programming breaks problems into subproblems",
         "Memoization caches results", "Fibonacci example: O(n) vs O(2^n)"], "drift": False, "overconf": False},

        # Day -1: Yesterday
        {"days_ago": 1, "topic": "Data Structures", "planned": 30, "actual": 28,
         "relevance": 80, "notes": ["Trees: hierarchical data structure", "BST: left < root < right",
         "Balanced trees maintain O(log n) operations"], "drift": False, "overconf": False},

        # Today
        {"days_ago": 0, "topic": "Python Basics", "planned": 25, "actual": 25,
         "relevance": 92, "notes": ["Context managers with 'with' statement",
         "__enter__ and __exit__ methods", "Great for resource cleanup"], "drift": False, "overconf": False},
    ]

    for d in demo_data:
        session_time = today - timedelta(days=d["days_ago"], hours=random.randint(8, 18))

        session = {
            "id": session_time.strftime("%Y%m%d_%H%M%S"),
            "topic": d["topic"],
            "planned_minutes": d["planned"],
            "actual_minutes": d["actual"],
            "start_time": session_time.isoformat(),
            "end_time": (session_time + timedelta(minutes=d["actual"])).isoformat(),
            "breaks": [],
            "total_break_time": 0,
            "notes": d["notes"],
            "ai_summary": f"Covered: {'; '.join(d['notes'][:2])}.",
            "topic_relevance_score": d["relevance"],
            "focus_feedback": "Good session!" if d["relevance"] >= 70 else "Room for improvement.",
            "completed": True,
            "topic_drift_detected": d["drift"],
            "drift_details": "Notes don't fully match the topic." if d["drift"] else "",
            "overconfidence_detected": d["overconf"],
            "overconfidence_details": "Passive consumption detected." if d["overconf"] else "",
            "revision_tasks": ["Review notes tomorrow", "Practice with exercises"],
            "next_session_plan": f"Continue with {d['topic']} focusing on practical application."
        }
        sessions.append(session)

    return sessions


def load_demo_mode():
    """Load demo data and display the app in showcase mode."""
    print("\n" + "═" * 50)
    print("  🎬 DEMO MODE")
    print("═" * 50)
    print("\n  Loading sample data for demonstration...")

    # Create demo data directory
    demo_dir = DATA_DIR / "demo_backup"
    demo_dir.mkdir(exist_ok=True)

    # Backup existing data if any
    if SESSIONS_FILE.exists():
        import shutil
        backup_file = demo_dir / f"sessions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy(SESSIONS_FILE, backup_file)
        print(f"  📁 Backed up existing data to {backup_file.name}")

    # Load demo sessions
    demo_sessions = generate_demo_sessions()
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({"sessions": demo_sessions}, f, indent=2)

    print(f"  ✅ Loaded {len(demo_sessions)} demo sessions")
    print("\n  Demo includes:")
    print("    • 12 study sessions over 2 weeks")
    print("    • 4 different topics")
    print("    • Examples of topic drift and overconfidence detection")
    print("    • Varied focus scores and session lengths")
    print("\n  You can now explore all features with realistic data!")

    input("\n  Press Enter to continue to main menu...")


# ============================================================================
# EXPORT FUNCTIONALITY
# ============================================================================

def export_weekly_report():
    """Export weekly report to a text file."""
    sessions = load_sessions()

    if not sessions:
        print("\n  No sessions to export!")
        return

    report = WeeklyReportGenerator.generate(sessions)
    overview = report["overview"]
    this_week = overview["this_week"]

    # Build report text
    lines = []
    lines.append("=" * 60)
    lines.append("SMART STUDY & FOCUS COMPANION - WEEKLY REPORT")
    lines.append("=" * 60)
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Week: {report['period']['start']} to {report['period']['end']}")

    # Streak
    streak = report["streak"]
    lines.append(f"\nCurrent Streak: {streak['current']} days")
    lines.append(f"Longest Streak: {streak['longest']} days")

    # Overview
    lines.append("\n" + "-" * 60)
    lines.append("OVERVIEW")
    lines.append("-" * 60)
    lines.append(f"Study Time: {this_week['time']:.0f} minutes ({this_week['time']/60:.1f} hours)")
    lines.append(f"Sessions: {this_week['sessions']}")
    lines.append(f"Average Score: {this_week['avg_relevance']:.0f}/100")
    lines.append(f"Focus Issues: {this_week['issues']} sessions")

    # Daily breakdown
    daily = report["daily_breakdown"]
    lines.append("\n" + "-" * 60)
    lines.append("DAILY BREAKDOWN")
    lines.append("-" * 60)
    for d in daily:
        if d["minutes"] > 0:
            lines.append(f"  {d['day']}: {d['minutes']:.0f} min (avg score: {d['avg_score']:.0f}%)")

    # Topics
    topics = report["topic_analysis"]
    if topics:
        lines.append("\n" + "-" * 60)
        lines.append("TOPICS STUDIED")
        lines.append("-" * 60)
        for t in topics:
            status = "✓" if t["understanding"] == "good" else "!" if t["understanding"] == "medium" else "X"
            lines.append(f"  [{status}] {t['topic']}: {t['time']:.0f} min, {t['sessions']} sessions, avg {t['avg_score']:.0f}%")

    # Time vs Retention
    tvr = report["time_vs_retention"]
    lines.append("\n" + "-" * 60)
    lines.append("TIME VS RETENTION ANALYSIS")
    lines.append("-" * 60)
    lines.append(f"  Short (<20m): {tvr['short_sessions']['count']} sessions, avg {tvr['short_sessions']['avg_score']:.0f}%")
    lines.append(f"  Medium (20-40m): {tvr['medium_sessions']['count']} sessions, avg {tvr['medium_sessions']['avg_score']:.0f}%")
    lines.append(f"  Long (40m+): {tvr['long_sessions']['count']} sessions, avg {tvr['long_sessions']['avg_score']:.0f}%")
    lines.append(f"  Optimal Duration: {tvr['optimal_duration']}")

    # Problem areas
    problems = report["problem_areas"]
    if problems:
        lines.append("\n" + "-" * 60)
        lines.append("AREAS NEEDING ATTENTION")
        lines.append("-" * 60)
        for p in problems:
            lines.append(f"  [{p['priority'].upper()}] {p['topic']}")
            for issue in p["issues"]:
                lines.append(f"      - {issue}")

    # Recommendations
    lines.append("\n" + "-" * 60)
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 60)
    for rec in report["recommendations"]:
        # Remove emoji for plain text
        clean_rec = re.sub(r'[^\w\s.,!?;:\'-]', '', rec).strip()
        lines.append(f"  * {clean_rec}")

    # Grade
    grade = cls_calculate_weekly_grade(this_week)
    lines.append("\n" + "=" * 60)
    lines.append(f"WEEKLY GRADE: {grade['letter']} ({grade['score']}/100)")
    lines.append(grade['message'])
    lines.append("=" * 60)

    # Write to file
    export_path = Path(__file__).parent / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(export_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  ✅ Report exported to: {export_path.name}")
    return export_path


# ============================================================================
# CLI ARGUMENT PARSING
# ============================================================================

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Smart Study & Focus Companion - AI-Powered Study Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python focus_companion.py              # Normal mode
  python focus_companion.py --demo       # Load demo data for showcase
  python focus_companion.py --export     # Export weekly report to file
  python focus_companion.py --stats      # Quick stats overview
        """
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Load demo data for showcasing the application"
    )

    parser.add_argument(
        "--export",
        action="store_true",
        help="Export weekly report to text file"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show quick statistics and exit"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all session data (with confirmation)"
    )

    return parser.parse_args()


def show_quick_stats():
    """Display quick statistics."""
    sessions = load_sessions()

    print("\n" + "═" * 50)
    print("  📊 QUICK STATS")
    print("═" * 50)

    if not sessions:
        print("\n  No sessions recorded yet.")
        return

    total_time = sum(s.actual_minutes for s in sessions)
    avg_score = sum(s.topic_relevance_score for s in sessions) / len(sessions)
    topics = set(s.topic for s in sessions)

    streak = WeeklyReportGenerator._calculate_streak(sessions)

    print(f"\n  Total Sessions: {len(sessions)}")
    print(f"  Total Study Time: {total_time:.0f} min ({total_time/60:.1f} hours)")
    print(f"  Average Focus Score: {avg_score:.0f}/100")
    print(f"  Topics Studied: {len(topics)}")
    print(f"  Current Streak: {streak['current']} days")
    print(f"  Longest Streak: {streak['longest']} days")

    # This week
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    this_week = [s for s in sessions
                 if datetime.fromisoformat(s.start_time).date() >= week_start]

    if this_week:
        week_time = sum(s.actual_minutes for s in this_week)
        print(f"\n  This Week: {len(this_week)} sessions, {week_time:.0f} min")


def reset_data():
    """Reset all session data with confirmation."""
    print("\n  ⚠️  This will delete ALL session data!")
    confirm = input("  Type 'DELETE' to confirm: ").strip()

    if confirm == "DELETE":
        if SESSIONS_FILE.exists():
            os.remove(SESSIONS_FILE)
        print("  ✅ All data has been reset.")
    else:
        print("  ❌ Reset cancelled.")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    args = parse_arguments()

    if args.demo:
        clear_screen()
        load_demo_mode()
        main_menu()
    elif args.export:
        export_weekly_report()
    elif args.stats:
        show_quick_stats()
    elif args.reset:
        reset_data()
    else:
        clear_screen()
        main_menu()
