# FUD-AI — False Understanding Detector
> **Detecting confidence that isn’t backed by understanding.**  
A reasoning-based AI system that evaluates conceptual understanding by probing consistency under variation, inspired by oral examinations.

---

## Overview
**FUD-AI** is an AI-powered “examiner” that identifies **false understanding** (illusion of competence) by stress-testing a learner’s reasoning through:
- **Socratic questioning** (why/how)
- **Counterfactual probes** (what changes if X changes?)
- **Consistency checks** (same concept, different framing)

Instead of only marking answers as right/wrong, FUD-AI detects **reasoning instability**, pinpoints the **exact misconception**, and generates a **targeted correction plan**.

---

## Problem Statement
Most learning systems today optimize for:
- correctness,
- recall,
- pattern-matching.

But real learning requires:
- transferable understanding,
- stable reasoning under variations,
- clarity in assumptions.

Students often appear confident but collapse when:
- the question is reframed,
- constraints change,
- real-world context is introduced.

This is **false understanding**, and it is one of the biggest hidden failure modes in education, interview prep, and upskilling.

---

## Solution
FUD-AI behaves like an **oral examiner**, not a tutor.

### What it does
1. Asks a core question (topic-specific)
2. Accepts free-form human answers
3. Evaluates reasoning quality (not just correctness)
4. Generates probing questions dynamically
5. Decides the next evaluation format (MCQ vs Text)
6. Produces:
   - verdict (correct / partial / misconception)
   - misconception explanation
   - improvement path

---

## Key Features
### ✅ Socratic Probing Engine
Asks “why/how” questions to expose hidden assumptions and shaky logic.

### ✅ Counterfactual Testing
Changes constraints and checks if understanding transfers.

Example:  
**“If the join condition changes, does your reasoning still hold?”**

### ✅ Consistency-Based Evaluation
Detects contradictions across multiple turns and rephrasings.

### ✅ Heuristic Mode Switch (MCQ vs Text)
If the gap is small → MCQ reinforcement  
If the gap is large → Text reasoning stress-test

### ✅ Session Memory & Traceability
Stores conversation turns with session IDs to:
- replay sessions,
- evaluate progression,
- power analytics.

### ✅ Media-to-Topics Bridge
Extracts key topics from documents/media text so QuestionGen focuses only on relevant concepts.

---

## Demo Use Case (Hackathon Flow)
**User goal:** “Test my SQL joins / PyTorch basics / TensorFlow fundamentals.”

**Flow:**
1. User selects topic or uploads notes
2. FUD-AI extracts topics (if media input exists)
3. Generates an exam question
4. User answers
5. Examiner agent evaluates and triggers probes
6. Heuristic decides MCQ vs Text next
7. System returns verdict + gap explanation + next steps

---

## System Architecture (High-Level)
**Frontend**
- Exam-style UI
- Displays question → probes → verdict
- Tracks progress and turn count

**Backend**
- Orchestrates sessions + endpoints
- Connects to OnDemand APIs
- Stores session turns

**OnDemand Agent Layer**
- Question Generation agent
- Examiner agent
- Probing agent
- MCQ agent
- Text Question agent
- Heuristic agent
- Result logger agent
- Extractor helper agent

**Tools (REST API tools used by agents)**
- SessionStateStore Tool (store/get conversation)
- Heuristic Decision Tool (mcq/text)
- Topic Extractor Bridge Tool (media → topics)

---

## Tech Stack (Detailed)

### Frontend
- **React** (UI)
- **Tailwind CSS** (styling)
- **Vite** (build tooling)
- **Axios / Fetch** (API calls)

### Backend
- **FastAPI** (high-performance Python API)
- **Uvicorn** (ASGI server)
- **Pydantic** (schema validation)
- **httpx** (async API requests)

### AI / Agent Orchestration
- **OnDemand Agents Framework**
- **OnDemand Chat API** (reasoning + probing + evaluation)
- **OnDemand Media API** (doc ingestion / extraction support)

### Session + Storage
- In-memory store for hackathon demo  
- *(Optional upgrade: Redis / PostgreSQL for production)*

### Deployment (Suggested)
- **Railway** (backend)
- **Vercel** (frontend)

---

## APIs & Tools (Endpoints)

### 1) SessionStateStore Tool
Stores and retrieves session turns.

**POST** `/session/store`  
Stores: `{session_id, turn, payload}`

**GET** `/session/get?session_id=...`  
Returns: session history array

---

### 2) Heuristic Decider Tool
Chooses next mode: MCQ or Text.

**POST** `/heuristic/decide`  
Input: `{gap_score, confidence_score, turns_so_far, last_verdict}`  
Output: `{mode, reason}`

---

### 3) Topic Extractor Bridge Tool
Extracts key topics from raw document text.

**POST** `/extract/topics`  
Input: `{raw_text, user_goal, max_topics}`  
Output: `{topics[], difficulty_hint, focus_constraints[]}`

---

## Agents (OnDemand)
The system uses multiple specialized agents to ensure modular reasoning:

1. **QuestionGen Agent**  
   Generates the base exam question from chosen topic / extracted topics.

2. **Examiner Agent**  
   Evaluates the answer and decides if probing is required.

3. **Probing Agent**  
   Generates Socratic + counterfactual probes.

4. **MCQ Gen Agent**  
   Creates quick checks for shallow gaps.

5. **Text Ques Gen Agent**  
   Generates deeper reasoning questions for large gaps.

6. **Heuristic Agent**  
   Routes evaluation type (MCQ vs Text).

7. **Result Logger Agent**  
   Summarizes performance + highlights recurring failure patterns.

8. **Extractor Helper Agent**  
   Bridges Media API output to structured topic focus.

---

## Installation & Setup

### Prerequisites
- Python **3.10+**
- Node.js **18+**
- OnDemand API credentials

---

### Backend Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
