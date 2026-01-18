from fastapi import FastAPI, Request, HTTPException
import json
import requests
import sys
from fastapi.middleware.cors import CORSMiddleware


# Script initialization message
print("LOADED: rag_api.py")

app = FastAPI()

# ===========================
# CONFIG
# ===========================
# API configuration and endpoint URLs

API_KEY = "eRJAi1NCS31pZlKUYGxzJq5AOG3ENCih"

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

CHAT_API_URL = "https://api.on-demand.io/automation/api/workflow/696c8350c28c63108ddbacaf/execute"
MEDIA_API_URL = "https://api.on-demand.io/automation/api/workflow/696aef27c28c63108ddb88bb/execute"
QUESTION_URL = "https://api.on-demand.io/automation/api/workflow/6969eaba27b1bb913e896a55/execute"
PROBE_URL = "https://api.on-demand.io/automation/api/workflow/696a0a07c28c63108ddb6316/execute"
STABILIZER_URL = "https://api.on-demand.io/automation/api/workflow/696a2dd127b1bb913e8974a1/execute"
MCQ_AGENT_URL = "https://api.on-demand.io/automation/api/workflow/696adf5327b1bb913e899b82/execute"
TEXT_AGENT_URL = "https://api.on-demand.io/automation/api/workflow/696ae12e27b1bb913e899c84/execute"
LOGGER_AGENT_URL = "https://api.on-demand.io/automation/api/workflow/696ae8888e6b21cb8aea6404/execute"

LOGGER_RESULTS = {}


# ===========================
# GLOBAL STATE (demo-scoped)
# ===========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # hackathon-safe
    allow_credentials=True,
    allow_methods=["*"],          # allows OPTIONS, POST, GET
    allow_headers=["*"],
)

# Maintains the current phase and data for the exam session

STATE = {
    "phase": "idle",          # idle | waiting_base | generating_probe | waiting_probe | analyzing
    "current_question": None,
    "current_concept": None,
    "base_answer": None,
    "probe_question": None,
    "probe_answer": None,
    "stability_result": None,
     "followup_question": None,
    "followup_type": None,
    "probe_count": 0
}

# ===========================
# CONCEPT INTEGRITY GATES
# ===========================

CONCEPT_SIGNATURES = {
    "joins": {
        "required": [" join "],
        "forbidden": [
            "subquery",
            "exists",
            "group by",
            "avg(",
            "sum(",
            "count(",
            "min(",
            "max(",
            "what aspect",
            "should the diagnostic",
            "execution order",
        ]
    },
    "subqueries": {
        "required": ["select"],
        "forbidden": [" join "]
    },
    "sql": {
        # SQL is a meta-trigger, not a testable concept
        "required": [],
        "forbidden": []
    }
}


# ===========================
# UTILITIES
# ===========================

def safe_parse_json(raw: str):
    """
    Safely extract JSON from noisy webhook payloads.
    Attempts to isolate JSON content from raw strings.
    """
    if not raw:
        return None

    raw = raw.strip()
    if "{" not in raw or "}" not in raw:
        return None

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        candidate = raw[start:end]
        candidate = bytes(candidate, "utf-8").decode("unicode_escape")
        return json.loads(candidate)
    except Exception:
        return None
    
def detect_learning_intent(text: str) -> dict:
    if not isinstance(text, str):
        return {"activate": False}

    t = text.lower()

    concept_map = {
        "joins": ["join", "joins", "left join", "right join", "inner join"],
        "indexes": ["index", "indexes"],
        "transactions": ["transaction", "commit", "rollback"],
        "subqueries": ["subquery", "exists"],
        "nulls": ["null", "is null"],
        "where_having": ["where", "having", "group by"],
        "sql": ["sql"]
    }

    intent_keywords = [
        "learn", "teach", "explain", "understand",
        "test", "practice", "quiz",
        "question", "questions", "problems"
    ]

    has_intent = any(k in t for k in intent_keywords)

    detected_concept = None
    for concept, keys in concept_map.items():
        if any(k in t for k in keys):
            detected_concept = concept
            break

    return {
        "activate": has_intent and detected_concept is not None,
        "topic": detected_concept
    }

# ===========================
# CHAT CONNECTOR (DELIVERY-SAFE)
# ===========================

@app.post("/chat")
async def chat_connector(request: Request):
    raw = await request.body()

    try:
        body = json.loads(raw)
    except Exception:
        body = raw.decode(errors="ignore")

    if isinstance(body, str):
        user_input = body.strip()
        session_id = "anonymous"
    elif isinstance(body, dict):
        user_input = body.get("user_input", "")
        session_id = body.get("session_id", "anonymous")
    else:
        return {"ok": False}

    if not user_input:
        return {"ok": True, "status": "empty"}

    intent = detect_learning_intent(user_input)

    if intent["activate"]:
        raw_concept = intent["topic"]

        if raw_concept == "sql":
            STATE["current_concept"] = "joins"   # default entry concept
        else:
            STATE["current_concept"] = normalize_concept(raw_concept)

        STATE["phase"] = "idle"   # exam-ready state

        requests.post(
            QUESTION_URL,
            json={
                "previous_topic": None,
                "concept": STATE["current_concept"]
            },
            headers=HEADERS
        )

        return {
            "ok": True,
            "mode": "exam_start",
            "message": f"Starting diagnostic on {STATE['current_concept']}."
        }


        return {
            "ok": True,
            "mode": "exam_start",
            "message": f"Starting diagnostic on {concept}."
        }


    # ---- Otherwise, just chat ----
    r = requests.post(
        CHAT_API_URL,
        json={
            "session_id": session_id,
            "user_input": user_input
        },
        headers=HEADERS
    )

    parsed = safe_parse_json(r.text) or {}
    execution_id = parsed.get("executionID")

    return {
        "ok": True,
        "status": "pending",
        "execution_id": execution_id
    }



@app.get("/chat/result/{execution_id}")
def get_chat_result(execution_id: str):
    if execution_id in CHAT_RESPONSES:
        return {
            "ok": True,
            "status": "complete",
            "text": CHAT_RESPONSES.pop(execution_id)
        }

    return {
        "ok": True,
        "status": "pending"
    }


# ===========================
# CHAT WEBHOOK RECEIVER
# ===========================

CHAT_RESPONSES = {}  # execution_id → response text

@app.post("/chat/webhook")
async def chat_webhook(request: Request):
    raw = (await request.body()).decode()
    print("RAW WEBHOOK BODY:", raw)
    sys.stdout.flush()

    payload = safe_parse_json(raw)

    # -------- Extract chat text --------
    if isinstance(payload, dict):
        text = (
            payload.get("text")
            or payload.get("outputs", {}).get("text")
        )
    else:
        text = raw.strip()

    if not text:
        return "OK"

    print("STORED CHAT RESPONSE:", text)
    sys.stdout.flush()


    return "OK"


@app.post("/media/extract")
async def media_knowledge_extract(request: Request):
    """
    Media Knowledge API
    Extracts readable text from media payloads.
    Also performs learning-intent detection.
    """
    raw = await request.body()

    # -------- HARD NORMALIZATION --------
    try:
        body = json.loads(raw)
    except Exception:
        body = raw.decode(errors="ignore")

    extracted_text = ""

    # Case 1: raw string
    if isinstance(body, str):
        extracted_text = body.strip()

    # Case 2: structured media payload
    elif isinstance(body, dict):
        extracted_text = (
            body.get("text")
            or body.get("raw_text")
            or body.get("content")
            or body.get("transcript")
            or ""
        )

        if isinstance(extracted_text, list):
            extracted_text = "\n".join(
                str(x) for x in extracted_text if isinstance(x, (str, int, float))
            )

        if not isinstance(extracted_text, str):
            extracted_text = str(extracted_text)

    else:
        extracted_text = str(body)

    extracted_text = extracted_text.strip()

    # -------- INTENT GATE --------
    intent = detect_learning_intent(extracted_text)

    if intent["activate"] and STATE["phase"] == "idle":
        STATE["current_concept"] = normalize_concept(intent["topic"])

        requests.post(
            QUESTION_URL,
            json={
                "previous_topic": None,
                "concept": STATE["current_concept"],
                "seed_text": extracted_text[:1500]
            },
            headers=HEADERS
        )

        return {
            "ok": True,
            "mode": "exam_start",
            "message": f"Starting diagnostic on {STATE['current_concept']} from uploaded content."
        }

    # -------- DEFAULT RESPONSE --------
    return {
        "ok": True,
        "mode": "media",
        "raw_text": extracted_text
    }


@app.post("/generate/media/extract")
async def media_knowledge_extract_alias(request: Request):
    """Alias for media knowledge extraction."""
    return await media_knowledge_extract(request)


@app.post("/generate/chat")
async def chat_connector_alias(request: Request):
    """Alias for chat connector."""
    return await chat_connector(request)


def normalize_concept(concept: str) -> str:
    """Normalizes concept names for internal logic routing."""
    if not concept:
        return "unknown"

    c = concept.lower()

    if "join" in c:
        return "joins"
    if "transaction" in c or "savepoint" in c:
        return "transactions"
    if "index" in c:
        return "indexes"
    if "null" in c:
        return "nulls"
    if "where" in c or "having" in c:
        return "where_having"
    if "union" in c or "intersect" in c or "except" in c:
        return "set_ops"
    if "key" in c or "constraint" in c:
        return "constraints"
    if "subquery" in c:
        return "subqueries"
    if "view" in c:
        return "views"

    return "unknown"


CANONICAL_KEYWORDS = {
    "joins": ["join", "left", "right", "inner", "outer", "full"],
    "transactions": ["transaction", "commit", "rollback", "savepoint"],
    "indexes": ["index", "scan", "btree", "gin", "bitmap"],
    "nulls": ["null", "coalesce", "nullif"],
    "where_having": ["where", "having", "group"],
    "set_ops": ["union", "intersect", "except"],
    "constraints": ["constraint", "unique", "foreign", "check", "exclude"],
    "subqueries": ["subquery", "exists", "correlated"],
    "views": ["view", "materialized", "refresh"]
}

# ===========================
# EXAM FLOW
# ===========================

# @app.get("/start_exam")
# def start_exam():
#     """Initializes the exam flow and generates the first question."""
#     if STATE["phase"] != "idle":
#         return {"message": "Exam already in progress"}

#     STATE.update({
#         "phase": "idle",
#         "current_question": None,
#         "current_concept": None,
#         "base_answer": None,
#         "probe_question": None,
#         "probe_answer": None,
#         "stability_result": None
#     })

#     requests.post(
#         QUESTION_URL,
#         json={"previous_topic": None},
#         headers=HEADERS
#     )

#     return {"message": "Exam started. Generating question."}




@app.post("/question")
async def question_webhook(request: Request):
    print("QUESTION WEBHOOK HIT")
    sys.stdout.flush()

    payload = safe_parse_json((await request.body()).decode())
    if not isinstance(payload, dict):
        return "OK"

    question = payload.get("question", "")
    concept = STATE["current_concept"]

    if not question or concept not in CONCEPT_SIGNATURES:
        return "OK"

    q = question.lower()
    sig = CONCEPT_SIGNATURES[concept]

    # 🚪 CONCEPT GATE
    if not any(k in q for k in sig["required"]):
        print("REJECTED: missing required concept signal")
        question = (
            "Table A has ids 1 and 2. "
            "Table B has id 2 only. "
            "Using LEFT JOIN A to B on id, which rows appear?"
        )

    if any(k in q for k in sig["forbidden"]):
        print("REJECTED: forbidden concept leakage")
        question = (
            "Table A has ids 1 and 2. "
            "Table B has id 2 only. "
            "Using LEFT JOIN A to B on id, which rows appear?"
        )

    # ✅ Accept question
    STATE["current_question"] = question
    STATE["phase"] = "waiting_base"

    return "OK"



@app.get("/question")
def get_question():
    phase = STATE["phase"]

    if phase == "waiting_base":
        return {
            "type": "base",
            "question": STATE["current_question"]
        }

    if phase == "waiting_probe":
        return {
            "type": "probe",
            "question": STATE["probe_question"]
        }

    if phase == "followup":
        return {
            "type": STATE["followup_type"],
            "question": STATE["followup_question"]
        }

    return {
        "status": "processing",
        "phase": phase
    }


@app.post("/answer")
async def submit_answer(request: Request):
    raw = await request.body()

    # -------- HARD NORMALIZATION --------
    try:
        body = json.loads(raw)
    except Exception:
        body = raw.decode(errors="ignore")

    if isinstance(body, str):
        answer = body.strip()
    elif isinstance(body, dict):
        answer = body.get("answer", "")
    else:
        answer = ""

    if not answer:
        return {"status": "empty answer ignored"}

    # ============================
    # BASE ANSWER → GENERATE PROBE
    # ============================
    if STATE["phase"] == "waiting_base":
        STATE["base_answer"] = answer
        STATE["phase"] = "generating_probe"

        # 🔴 FIX 1: Correct payload for Probe Agent
        r = requests.post(
            PROBE_URL,
            json={
                "concept": STATE["current_concept"],
                "previous_question": STATE["current_question"],
                "user_answer": answer
            },
            headers=HEADERS
        )

        parsed = safe_parse_json(r.text)

        # 🔴 FIX 2: Correct key name from probe output
        probe_q = (
            parsed.get("followup_question")
            if isinstance(parsed, dict)
            else None
        )

        if isinstance(probe_q, str) and probe_q.strip():
            STATE["probe_question"] = probe_q.strip()
        else:
            # HARD GUARANTEE — NEVER STALL THE EXAM
            STATE["probe_question"] = (
                "Explain your reasoning step by step."
            )

        STATE["phase"] = "waiting_probe"
        return {"status": "Base answer received"}

    # ============================
    # PROBE ANSWER → STABILIZER
    # ============================
    if STATE["phase"] == "waiting_probe":
        STATE["probe_answer"] = answer
        STATE["phase"] = "analyzing"

        requests.post(
            STABILIZER_URL,
            json={
                "base_question": STATE["current_question"],
                "base_answer": STATE["base_answer"],
                "probe_question": STATE["probe_question"],
                "probe_answer": answer,
                "concept_id": STATE["current_concept"]
            },
            headers=HEADERS
        )

        return {"status": "Probe answer received"}

    return {"status": "answer ignored", "phase": STATE["phase"]}

# ===========================
# PROBE HANDLING
# ===========================

@app.post("/probe")
async def probe_webhook(request: Request):
    STATE["probe_count"] += 1
    raw = (await request.body()).decode()
    payload = safe_parse_json(raw)

    print("PROBE PAYLOAD (telemetry only):", payload)
    sys.stdout.flush()


    return "OK"



@app.get("/probe")
def get_probe(session_id: str = "anonymous"):
    probes = [
        x for x in SESSION_STORE.get(session_id, [])
        if x.get("role") == "probe"
    ]

    if not probes:
        return {"status": "no probe yet"}

    return probes[-1]


@app.get("/session/probes/{session_id}")
def get_probes(session_id: str):
    return [
        x for x in SESSION_STORE.get(session_id, [])
        if x.get("role") == "probe"
    ]

# ===========================
# STABILIZER
# ===========================

@app.post("/stabilizer")
async def stabilizer_webhook(request: Request):
    raw = (await request.body()).decode()
    payload = safe_parse_json(raw)

    print("STABILIZER PAYLOAD:", payload)
    sys.stdout.flush()

    if not isinstance(payload, dict):
        return "OK"

    confidence = float(payload.get("confidence", 0.5))
    gap = float(payload.get("gap_score", 1.0 - confidence))

    # Store stability result for UI
    STATE["stability_result"] = {
        "confidence": confidence,
        "gap_score": gap,
        "understanding": payload.get("understanding"),
        "failure_point": payload.get("failure_point")
    }

    if confidence < 0.7 and STATE.get("probe_count", 0) < 2:
        STATE["probe_question"] = "Explain this again with a simple analogy."
        STATE["phase"] = "waiting_probe"
        return "OK"



   
    turns = len(SESSION_STORE.get("anonymous", []))
    mode = "mcq" if gap >= 0.4 or turns < 2 else "text"
    STATE["followup_type"] = mode

    try:
        if mode == "mcq":
            r = requests.post(
                "http://127.0.0.1:8000/generate/mcq",
                json={
                    "concept": STATE["current_concept"],
                    "base_question": STATE["current_question"],
                    "base_answer": STATE["probe_answer"],
                    "gap_score": gap,
                    "confidence_score": confidence
                }
            )
            STATE["followup_question"] = r.json()



        else:
            r = requests.post(
                "http://127.0.0.1:8000/generate/text",
                json={
                    "concept": STATE["current_concept"],
                    "base_question": STATE["current_question"],
                    "base_answer": STATE["probe_answer"]
                }
            )
            STATE["followup_question"] = r.json()

        STATE["phase"] = "followup"

    except Exception as e:
        print("FOLLOWUP GENERATION ERROR:", e)
        STATE["phase"] = "error"

    return "OK"



# ===========================
# HEURISTIC DECISION TOOL
# ===========================

@app.post("/heuristic/decide")
async def decide_question_mode(request: Request):
    """Determines whether to show an MCQ or a Text probe based on user performance scores."""
    body = await request.json()

    try:
        gap_score = float(body.get("gap_score", 0.0))
        confidence_score = float(body.get("confidence_score", 0.0))
        turns_so_far = int(body.get("turns_so_far", 0))
    except Exception as e:
        return {
            "mode": "mcq",
            "reason": f"Invalid heuristic inputs: {str(e)}"
        }

    if turns_so_far < 2:
        return {"mode": "mcq", "reason": "Early session stabilization."}

    if gap_score >= 0.6 and confidence_score <= 0.4:
        return {"mode": "mcq", "reason": "Large gap with low confidence."}

    if gap_score >= 0.4 and confidence_score < 0.6:
        return {"mode": "mcq", "reason": "Partial understanding detected."}

    if gap_score < 0.4 and confidence_score >= 0.6:
        return {"mode": "text", "reason": "Low gap with high confidence."}

    return {"mode": "text", "reason": "Defaulting to open-ended reasoning."}

@app.post("/generate/mcq")
async def generate_mcq_probe(request: Request):
    raw = await request.body()

    try:
        body = json.loads(raw)
    except Exception:
        body = {}

    response = requests.post(
        MCQ_AGENT_URL,
        json=body,
        headers=HEADERS
    )

    parsed = safe_parse_json(response.text)

    # 🚨 ABSOLUTE GUARANTEE FOR FRONTEND
    if not isinstance(parsed, dict) or "question" not in parsed:
        return {
            "question_type": "mcq",
            "question": "Which statement is correct?",
            "options": {
                "A": "LEFT JOIN keeps unmatched left rows",
                "B": "INNER JOIN removes unmatched rows",
                "C": "FULL JOIN keeps all rows",
                "D": "RIGHT JOIN keeps unmatched right rows"
            }
        }

    options = parsed.get("options")

    if not isinstance(options, dict) or len(options) != 4:
        options = {
            "A": "Option A",
            "B": "Option B",
            "C": "Option C",
            "D": "Option D"
        }

    return {
        "question_type": "mcq",
        "question": parsed.get("question"),
        "options": options
    }



@app.post("/generate/text")
async def generate_text_probe(request: Request):
    """Interacts with the Text agent to create an open-ended probe question."""
    raw = await request.body()

    try:
        body = json.loads(raw)
    except Exception:
        body = raw.decode()

    # HARD NORMALIZATION
    if isinstance(body, str):
        body = {
            "concept": None,
            "base_question": body,
            "base_answer": None,
            "gap_score": 0.5,
            "confidence_score": 0.5
        }

    if not isinstance(body, dict):
        raise HTTPException(400, "Invalid text probe input payload")

    response = requests.post(
        TEXT_AGENT_URL,
        json=body,
        headers=HEADERS
    )

    raw_output = response.text
    print("RAW TEXT AGENT OUTPUT:\n", raw_output)
    sys.stdout.flush()

    parsed = safe_parse_json(raw_output)

    # HARD FALLBACK
    if not isinstance(parsed, dict):
        return {
            "question_type": "text",
            "question": raw_output.strip()
        }

    # NORMALIZATION
    question = (
        parsed.get("question")
        or parsed.get("probe")
        or parsed.get("prompt")
        or parsed.get("text")
    )

    if not isinstance(question, str):
        return {
            "question_type": "text",
            "question": raw_output.strip()
        }

    return {
        "question_type": "text",
        "question": question.strip()
    }

# ===========================
# LOGGER (EXPLANATION DIAGNOSTICS)
# ===========================

LOGGER_RESULTS = {}

@app.post("/logger/analyze")
async def run_logger(request: Request):
    """Analyzes session history to identify explanation gaps."""
    raw = await request.body()

    # HARD NORMALIZATION
    try:
        body = json.loads(raw)
    except Exception:
        body = raw.decode()

    # If body is string -> treat as session_id
    if isinstance(body, str):
        session_id = body
    elif isinstance(body, dict):
        session_id = body.get("session_id")
    else:
        session_id = None

    if not isinstance(session_id, str):
        # Never fail delivery
        return {
            "ok": False,
            "reason": "Missing session_id"
        }

    # FETCH HISTORY INTERNALLY
    session_history = SESSION_STORE.get(session_id, [])

    # Call LOGGER AGENT
    response = requests.post(
        LOGGER_AGENT_URL,
        json={
            "session_id": session_id,
            "session_history": session_history
        },
        headers=HEADERS
    )

    raw_output = response.text
    print("RAW LOGGER AGENT OUTPUT:\n", raw_output)
    sys.stdout.flush()

    parsed = safe_parse_json(raw_output)

    # HARD FALLBACK
    if not isinstance(parsed, dict):
        parsed = {
            "diagnosis": [],
            "summary": "Unable to identify explanation gaps from session history."
        }

    LOGGER_RESULTS[session_id] = parsed

    return {
        "ok": True,
        "session_id": session_id,
        "issues_found": len(parsed.get("diagnosis", []))
    }

@app.post("/generate/logger/analyze")
async def run_logger_alias(request: Request):
    """Alias for running the logger analyze functionality."""
    return await run_logger(request)


# ===========================
# SESSION MEMORY (STORE)
# ===========================

# Simple in-memory session store (demo / hackathon scope)
SESSION_STORE = {}

@app.post("/session/store")
async def store_session_turn(request: Request):
    """Stores individual conversation turns into the in-memory session store."""
    raw = await request.body()

    try:
        body = json.loads(raw)
    except Exception:
        return {"ok": False}

    if not isinstance(body, dict):
        return {"ok": False}

    session_id = body.get("session_id")
    turn = body.get("turn")
    payload = body.get("payload")

    # Hard validation (never crash)
    if not isinstance(session_id, str):
        return {"ok": False}

    if not isinstance(turn, int):
        return {"ok": False}

    if not isinstance(payload, dict):
        return {"ok": False}

    # Initialize session if needed
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []

    # Enforce monotonic turn ordering (soft)
    SESSION_STORE[session_id].append({
        "turn": turn,
        "payload": payload
    })

    return {"ok": True}

@app.post("/generate/session/store")
async def store_session_turn_alias(request: Request):
    """Alias for storing session turn data."""
    return await store_session_turn(request)

@app.post("/exam/next")
def exam_next():
    phase = STATE["phase"]

    if phase == "idle":
        requests.post(
            QUESTION_URL,
            json={"previous_topic": STATE.get("current_concept")},
            headers=HEADERS
        )
        return {"status": "generating_question"}

    if phase == "waiting_base":
        return {
            "type": "question",
            "question": STATE["current_question"]
        }

    if phase == "generating_probe":
        return {"status": "generating_probe"}

    if phase == "waiting_probe":
        return {
            "type": "probe",
            "question": STATE["probe_question"]
        }

    if phase == "analyzing":
        return {"status": "analyzing"}

    return {"status": "waiting"}



# ===========================
# STATUS / RESULT
# ===========================

@app.get("/result")
def get_result():
    """Retrieves the latest stability verdict result."""
    return STATE["stability_result"] or {"status": "no result yet"}


@app.get("/status")
def status():
    """Retrieves current phase and concept state."""
    return {
        "phase": STATE["phase"],
        "concept": STATE["current_concept"]
    }