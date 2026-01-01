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

            # Show if issues detected recently
            recent_issues = sum(1 for s in sessions[-5:]
                              if s.topic_drift_detected or s.overconfidence_detected)
            if recent_issues > 0:
                print(f"  ⚠️  {recent_issues}/5 recent sessions had focus issues")

        api_status = "Claude API ✓" if ANTHROPIC_API_KEY else "Local analysis"
        print(f"  🤖 AI: {api_status}")

        print("\n" + "─" * 50)
        print("\n  [1] 📚 Start Study Session")
        print("  [2] 📜 View History")
        print("  [3] 🚪 Exit")

        choice = input("\n  Select: ").strip()

        if choice == "1":
            clear_screen()
            start_session()
            input("\n  Press Enter to continue...")
        elif choice == "2":
            clear_screen()
            display_history()
            input("\n  Press Enter to continue...")
        elif choice == "3":
            print("\n  👋 Keep learning!\n")
            break


if __name__ == "__main__":
    clear_screen()
    main_menu()
