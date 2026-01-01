# Decision Log

> Technical decisions made during development, with rationale.

## Overview

This document explains the "why" behind key architectural and algorithmic choices. Useful for interviews, code reviews, and future maintenance.

---

## Decision 1: Heuristics Over Machine Learning

### Context
Topic drift and overconfidence detection could theoretically use ML models (embeddings, classifiers).

### Decision
Use rule-based heuristics with keyword matching.

### Rationale

| Factor | Heuristics | ML Model |
|--------|-----------|----------|
| **Transparency** | Explainable rules | Black box |
| **Data requirement** | Works immediately | Needs training data |
| **Offline capability** | Full functionality | Requires API/model |
| **Maintenance** | Simple to update | Model drift, retraining |
| **Latency** | Instant | Model inference time |

### Trade-offs Accepted
- Less accurate semantic understanding
- May miss subtle topic drift
- Limited to English keywords

### Why This Is Correct
For a study tracking tool, **explainability matters more than accuracy**. A student needs to understand *why* the system flagged their session, not just that it did. Rule-based systems provide this naturally.

---

## Decision 2: Optional AI Layer

### Context
The app can use Claude API for enhanced analysis.

### Decision
Design the system to work fully without any API. AI is an enhancement layer.

### Rationale
1. **Accessibility**: Not everyone has API access or credits
2. **Reliability**: Offline-first design means no dependency on external services
3. **Testing**: Deterministic behavior makes testing straightforward
4. **Cost**: No API costs for basic functionality

### Implementation
```python
if ANTHROPIC_API_KEY:
    return cls._analyze_with_claude(...)
else:
    return cls._analyze_locally(...)
```

Every AI-powered function has a local fallback.

---

## Decision 3: JSON Over SQLite

### Context
Session data needs to be persisted locally.

### Decision
Use JSON file storage instead of SQLite.

### Rationale

| Factor | JSON | SQLite |
|--------|------|--------|
| **Simplicity** | No schema, no ORM | Requires schema design |
| **Portability** | Human-readable, easy backup | Binary format |
| **Dependencies** | None | sqlite3 (stdlib, but still) |
| **Debugging** | Open in any text editor | Need DB viewer |
| **Scale** | Fine for <10k sessions | Better for large data |

### Trade-offs Accepted
- No query optimization
- Full file read/write on each operation
- No transactions/ACID guarantees

### Why This Is Correct
For personal study tracking, data volume is low (maybe 1000 sessions/year). JSON simplicity wins. SQLite would be over-engineering.

---

## Decision 4: Multi-Factor Focus Scoring

### Context
Need a single "focus score" metric for each session.

### Decision
Use weighted combination of multiple factors.

### Factors and Weights
```python
{
    "completion_ratio": 0.20,     # Finished planned time?
    "distraction_penalty": 0.25,  # Fewer distractions = better
    "self_rating": 0.15,          # User's own assessment
    "time_of_day_bonus": 0.10,    # Peak hours boost
    "consistency_bonus": 0.15,    # Regular study habits
    "retention_score": 0.15       # Quiz/note quality
}
```

### Rationale
1. **Multiple signals**: No single metric captures focus quality
2. **Weighted combination**: Allows tuning based on importance
3. **Transparent formula**: Users can understand their score
4. **Extensible**: Easy to add new factors

### Alternative Considered
Binary good/bad classification. Rejected because:
- Loses nuance
- Harder to track improvement
- Less motivating for users

---

## Decision 5: Passive vs Active Language Detection

### Context
Need to detect "overconfidence" — when users consume content without retention.

### Decision
Compare passive vocabulary ("watched", "read", "saw") vs active vocabulary ("learned", "because", "therefore").

### Rationale

**Passive indicators** suggest content consumption:
- "Watched video about..."
- "Read the chapter on..."
- "Saw the explanation of..."

**Active indicators** suggest processing and understanding:
- "Learned that X because Y"
- "Therefore, the algorithm works by..."
- "For example, when we apply..."

### Implementation
```python
PASSIVE = ["watched", "read", "saw", "video", "lecture"]
ACTIVE = ["learned", "because", "therefore", "example", "realized"]

if passive_count > 0 and active_count == 0:
    → Overconfidence warning
```

### Limitations
- Simple keyword matching
- May have false positives/negatives
- English-specific

### Why This Is Correct
The goal is to **prompt reflection**, not make judgments. Even if detection isn't perfect, the warning encourages users to think about their note quality.

---

## Decision 6: Dual Interface Architecture (CLI + Web)

### Context
Could build web UI, desktop app, or CLI.

### Decision
Build CLI first, then add a web layer that reuses the core engine.

### Implementation

```
focus_companion.py     ← Core engine + CLI interface
        ↓
api/main.py            ← FastAPI REST wrapper (imports core classes)
        ↓
web/                   ← React + TypeScript frontend
```

### Rationale
1. **CLI-first**: Core logic developed without UI complexity
2. **Shared core**: API imports from `focus_companion.py` — no code duplication
3. **Technology choices**:
   - FastAPI: Modern, async, auto-generated OpenAPI docs
   - React 19: Latest features, excellent TypeScript support
   - Tailwind CSS: Rapid styling without CSS files
   - Chart.js: Lightweight visualization

### Trade-offs Accepted
- Two runtimes (Python + Node) for full stack
- CORS configuration required for local dev
- Frontend build step adds complexity

### Why This Is Correct
The architecture validates the original design: **core logic is UI-agnostic**. The same `AIEngine`, `TopicDriftDetector`, and `WeeklyReportGenerator` classes power both interfaces.

---

## Decision 7: Weekly Grading System

### Context
Users need a summary of their weekly performance.

### Decision
Calculate a letter grade (A+ to F) based on three components.

### Grading Formula
```python
score = 0
score += min(40, (time / 300) * 40)           # Time: max 40pts
score += (avg_relevance / 100) * 40           # Quality: max 40pts
score += min(20, sessions * 4)                # Consistency: max 20pts
score -= issues * 5                           # Penalty per issue

# Map to letter grade
90+ → A+
80+ → A
70+ → B
60+ → C
50+ → D
<50 → F
```

### Rationale
1. **Familiar format**: Everyone understands letter grades
2. **Balanced weighting**: Time alone isn't enough
3. **Motivating**: Clear improvement targets
4. **Gamification**: Without being gimmicky

---

## Decision 8: Demo Mode with Realistic Data

### Context
Need to showcase the app in interviews/demos.

### Decision
Create `--demo` flag that loads 12 realistic sample sessions.

### Demo Data Characteristics
- Spans 2 weeks
- 4 different topics
- Mix of good and problematic sessions
- Includes topic drift and overconfidence examples
- Natural variation in scores

### Why This Matters
Interviewers want to see the system in action, not wait while you create sessions manually. Demo mode provides instant showcase capability.

---

## Summary

| Decision | Principle Applied |
|----------|-------------------|
| Heuristics over ML | Explainability > accuracy |
| Optional AI | Offline-first, degrade gracefully |
| JSON storage | Simplicity > scalability (for this use case) |
| Multi-factor scoring | Nuance > binary classification |
| Passive/active detection | Prompt reflection, not judgment |
| Dual interface (CLI + Web) | Core logic is UI-agnostic |
| Weekly grading | Familiar + motivating |
| Demo mode | Interview-readiness |

---

*Last updated: January 2026*
