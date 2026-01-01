# Smart Study & Focus Companion

> **AI-Powered Study Tracker** — Measure learning quality, not just time spent.

A Python CLI application that helps students study smarter by tracking focus quality, detecting passive learning patterns, and providing actionable feedback.

## Problem Statement

Students commonly face these challenges:

| Problem | Impact |
|---------|--------|
| **Time ≠ Learning** | Hours spent studying doesn't correlate with retention |
| **Passive Consumption** | Watching videos without active engagement |
| **No Feedback Loop** | No way to measure if study methods are working |
| **Topic Drift** | Starting with one topic, ending somewhere else |
| **Overconfidence** | Feeling like you understand, but failing to recall |

This tool provides **data-driven insights** into study effectiveness, not just time tracking.

## Core Insight

> "The illusion of learning is watching a 2-hour lecture and feeling like you understand. Real learning is being able to explain it without notes."

This application detects the gap between *perceived* understanding and *actual* retention.

## Features

### Phase 1: Core Tracking
- Focus timer with break tracking
- Post-session note-taking (3-5 bullet points)
- AI-powered note summarization
- Topic relevance scoring (0-100)

### Phase 2: Intelligent Detection
- **Topic Drift Detection** — Identifies when notes don't match stated topic
- **Overconfidence Detection** — Flags passive consumption patterns
- **Revision Task Generation** — Actionable next steps
- **Next Session Planning** — Context-aware recommendations

### Phase 3: Weekly Analytics
- Study time vs. retention analysis
- Daily breakdown with CLI charts
- Problem area identification
- Weekly grade with personalized feedback

## Quick Start

### Option 1: CLI Mode

```bash
# Normal mode
python focus_companion.py

# Demo mode (preloaded sample data)
python focus_companion.py --demo

# Export weekly report
python focus_companion.py --export

# Quick stats
python focus_companion.py --stats
```

### Option 2: Web Application

```bash
# Start the FastAPI backend
cd api
pip install fastapi uvicorn
python main.py
# API runs at http://localhost:8000

# In a new terminal, start the React frontend
cd web
npm install
npm run dev
# Web app runs at http://localhost:5173
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                         │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │      CLI (Python)       │  │    Web App (React)      │  │
│  │   focus_companion.py    │  │    localhost:5173       │  │
│  └───────────┬─────────────┘  └───────────┬─────────────┘  │
└──────────────┼────────────────────────────┼────────────────┘
               │                            │
               │              ┌─────────────▼─────────────┐
               │              │    FastAPI Backend        │
               │              │    localhost:8000         │
               │              └─────────────┬─────────────┘
               │                            │
┌──────────────▼────────────────────────────▼────────────────┐
│                   CORE ENGINE (Python)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Timer     │  │   Notes     │  │   Breaks    │         │
│  │  Tracking   │  │  Collection │  │  Tracking   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   AI ANALYSIS ENGINE                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Topic Drift    │  Overconfidence  │  Focus Score      ││
│  │  Detector       │  Detector        │  Calculator       ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Revision Task  │  Next Session    │  Weekly Report    ││
│  │  Generator      │  Planner         │  Generator        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   DATA PERSISTENCE                          │
│                    (JSON Storage)                           │
└─────────────────────────────────────────────────────────────┘
```

## Key Algorithms

### 1. Focus Scoring (Multi-Factor Weighted)

```python
WEIGHTS = {
    "completion_ratio": 0.25,    # Did you finish?
    "note_quality": 0.25,        # How detailed are notes?
    "topic_relevance": 0.20,     # Do notes match topic?
    "time_of_day": 0.15,         # Peak hours bonus
    "consistency": 0.15          # Regular study habits
}
```

### 2. Topic Drift Detection

Detects when notes don't match the stated study topic using:
- Keyword overlap analysis
- Subject area classification
- Vague language detection ("stuff", "things", "basically")

```
Topic: "Binary Search Trees"
Notes: "Watched video about loops and functions"
→ DRIFT DETECTED: Notes show low relevance (35%)
```

### 3. Overconfidence Detection

Identifies passive learning patterns:

| Signal | Detection Method |
|--------|-----------------|
| Passive language | "watched", "read", "saw" without "learned", "because" |
| Sparse notes | Long session + minimal notes |
| No active recall | Missing explanation/application |

```
Session: 45 minutes
Notes: "Watched neural network video. Saw backpropagation."
→ OVERCONFIDENCE: Notes describe content, not understanding.
```

## AI Philosophy

> "AI assists understanding — it never replaces reasoning."

This project uses **purpose-driven AI**:

- **With API**: Claude enhances summarization and generates smarter revision tasks
- **Without API**: Rule-based heuristics provide the same core functionality

The system is designed to work offline with deterministic rules. The AI layer is an enhancement, not a dependency.

## Sample Output

```
══════════════════════════════════════════════════
  AI ANALYSIS
══════════════════════════════════════════════════

  SUMMARY:
     Covered: Binary search requires sorted array;
     Time complexity O(log n).

  TOPIC RELEVANCE: 82/100
     Notes align well with topic

  FOCUS FEEDBACK:
     Great time management! Good note-taking effort.

──────────────────────────────────────────────────
  SESSION STATS:
     • Planned: 25 min
     • Actual: 24.5 min
     • Breaks: 1
     • Completion: 98%

══════════════════════════════════════════════════
  REVISION TASKS
══════════════════════════════════════════════════

  1. Implement binary search without looking at notes
  2. Explain to someone why it requires sorted input
  3. Tomorrow: Quiz yourself on time complexity
```

## Project Structure

```
project/
├── focus_companion.py        # Core engine + CLI interface
├── api/
│   ├── __init__.py
│   └── main.py               # FastAPI REST backend
├── web/
│   ├── src/
│   │   ├── components/       # React UI components
│   │   ├── pages/            # Dashboard, History, NewSession
│   │   ├── api.ts            # API client
│   │   └── App.tsx           # Router setup
│   └── package.json
├── data/
│   └── sessions.json         # All study sessions
└── weekly_report_*.txt       # Exported reports
```

## Limitations

1. **No true semantic understanding** — Topic relevance uses keyword matching, not embeddings
2. **Self-reported data** — Relies on honest note-taking
3. **English only** — Keyword detection optimized for English

## Future Enhancements

- [x] Web dashboard with visualizations
- [ ] Spaced repetition integration
- [ ] Mobile companion app for quick logging
- [ ] Research-backed scoring weights
- [ ] Export to Notion/Obsidian

## Tech Stack

| Component | Technology |
|-----------|------------|
| Core Engine | Python 3.8+ |
| Backend | FastAPI + Uvicorn |
| Frontend | React 19 + TypeScript + Tailwind CSS |
| Charts | Chart.js + react-chartjs-2 |
| AI (optional) | Claude API |
| Storage | JSON |

## Installation

```bash
# Clone the repository
git clone https://github.com/Muhammad-Ramzan381/Smart-Study-Focus-Companion.git
cd Smart-Study-Focus-Companion

# (Optional) Set up API key for enhanced AI features
export ANTHROPIC_API_KEY=your-key-here

# Option A: Run CLI
python focus_companion.py

# Option B: Run Web App
pip install fastapi uvicorn
cd api && python main.py &
cd web && npm install && npm run dev
```

## License

MIT License - See LICENSE file for details.

---

Built with a focus on **learning quality over quantity**.
