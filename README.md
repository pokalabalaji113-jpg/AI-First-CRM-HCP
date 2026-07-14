# 🧬 AI-First CRM — HCP Module · Log Interaction Screen

An **AI-first Customer Relationship Management (CRM)** tool for pharmaceutical field
representatives to log their interactions with **Healthcare Professionals (HCPs — e.g.
doctors)**.

> **The big idea:** The rep **never fills the form by hand**. They simply *talk* to an
> **AI Assistant** — and a **LangGraph agent powered by a Groq LLM** logs, edits, erases,
> searches, and suggests follow-ups by driving the form for them.

---

## 📑 Table of Contents
1. [Project Statement](#-1-project-statement)
2. [Tech Stack (with explanation)](#-2-tech-stack-with-explanation)
3. [The LLM — the brain](#-3-the-llm--the-brain)
4. [LangGraph — the agent framework](#-4-langgraph--the-agent-framework)
5. [The LangGraph Agent & Tool Orchestration](#-5-the-langgraph-agent--tool-orchestration)
6. [The 5 Tools (clear behaviour of each)](#-6-the-5-tools-clear-behaviour-of-each)
7. [Main Project Flow](#-7-main-project-flow)
8. [PostgreSQL — the database](#-8-postgresql--the-database)
9. [Frontend explained](#-9-frontend-explained)
10. [Backend explained](#-10-backend-explained)
11. [Project structure](#-11-project-structure)
12. [How to run](#-12-how-to-run)
13. [Try these prompts](#-13-try-these-prompts)
14. [Challenges faced & fixes](#-14-challenges-faced--fixes)
15. [Conclusion](#-15-conclusion)

---

## 🎯 1. Project Statement

Pharma sales reps meet many doctors every day. After each meeting they must record what
happened — the doctor's name, the topics discussed, samples given, the doctor's reaction
(sentiment), and the next steps. Doing this in a long manual form is slow.

This project designs the **"Log Interaction Screen"** the *AI-first* way. It has two parts:

| LEFT — *Interaction Details* | RIGHT — *AI Assistant* |
|------------------------------|------------------------|
| A full form (dropdowns, date/time pickers, Search/Add & Add-Sample buttons, radio sentiment, and a 🎤 *Summarize from Voice Note* button) that **looks** like a normal CRM form. | A **chat** where the rep describes the interaction in plain English (or speaks it). |
| 🔒 **Every field is disabled for manual typing** — it only mirrors the AI's state. | 🤖 The **only** way to fill / edit / erase the form. |

**Result:** the form is a live, read-only *display*; the **AI does 100% of the work**.

---

## 🧰 2. Tech Stack (with explanation)

| Layer | Technology | Why it is used |
|-------|-----------|----------------|
| **Frontend** | **React** | Builds the two-panel user interface. |
| | **Redux Toolkit** | Central store — holds the form + chat state; the AI updates it, the UI re-renders. |
| | **Vite** | Fast dev server + build tool. |
| | **Google Inter font** | Clean, modern typography (assignment requirement). |
| **Backend** | **Python + FastAPI** | Receives the chat message and returns the AI reply + updated form. Fast and simple. |
| **AI** | **LangGraph** *(mandatory)* | The agent framework that orchestrates the LLM and the tools. |
| | **Groq — `llama-3.3-70b-versatile`** *(LLM, mandatory)* | The "brain" that understands language and picks tools. Runs very fast on Groq. |
| **Database** | **PostgreSQL** | Stores every interaction permanently (SQLAlchemy ORM). |

> ⚠️ **Model note:** The assignment named `gemma2-9b-it`, but Groq **decommissioned** that
> model (API returns `400 model_decommissioned`). We use **`llama-3.3-70b-versatile`**,
> which the assignment explicitly allows and which supports tool-calling well. It is one
> env var (`GROQ_MODEL`) — swap it anytime in `backend/.env`.

---

## 🧠 3. The LLM — the brain

An **LLM (Large Language Model)** is an AI that understands and generates human language.
In this project the LLM is the **decision-maker**:

- It **reads** the rep's message (e.g. *"Met Dr. Sharma, positive, gave 2 samples"*).
- It **extracts** the entities (HCP name = Dr. Sharma, sentiment = Positive, samples = 2).
- It **decides which tool** to call (here: `log_interaction`).

We access the LLM through **Groq** — a platform that hosts open models and runs them at
very high speed with a free API key. **Groq is the runner; `llama-3.3-70b-versatile` is
the model.** Nothing about tool-selection or extraction is hardcoded — the LLM does it.

---

## 🕸️ 4. LangGraph — the agent framework

**LangGraph** lets us build the AI as a **graph** (a flow chart) of steps. Instead of a
plain "one question → one answer" chatbot, LangGraph gives us a **loop**:

```
think  →  call a tool  →  read the result  →  think again  →  … →  reply
```

This is exactly what an "agent" needs, because one request may require choosing among
many tools. LangGraph manages the state, the tool calls, and the loop for us.

---

## 🤖 5. The LangGraph Agent & Tool Orchestration

**Role of the agent:** it is the **single brain** of the Log Interaction Screen. The rep
talks to it in plain language; the agent decides which tool to run, extracts the entities,
drives the form state, and saves to PostgreSQL. **No form logic is hardcoded.**

**The graph has two nodes:**

```
              ┌─────────────────────┐
   START ───▶ │       agent         │   ← Groq LLM with the 5 tools "bound" to it
              │  (decides an action)│
              └──────────┬──────────┘
                         │  tools_condition
        (LLM asked for a tool)│         (no tool needed)
                         ▼                     └────────▶ END (reply to user)
              ┌─────────────────────┐
              │        tools        │   ← runs the chosen tool, updates form_data
              └──────────┬──────────┘
                         └──── back to agent ────┘
```

**Tool orchestration** = the agent listens, picks the correct tool, runs it, and (if
needed) calls another, all in the right order. A `MemorySaver` checkpointer keyed by a
per-session `thread_id` remembers the conversation + form across turns.

**Key design rule:** the LLM is set to call **one tool per turn** (`parallel_tool_calls=False`),
and `form_data` uses a **merge reducer**, so tool updates never clash.

---

## 🛠️ 6. The 5 Tools (clear behaviour of each)

All 5 live in [`backend/app/agent/tools.py`](backend/app/agent/tools.py) and are driven by
the LLM — none are hardcoded.

### 1️⃣ `log_interaction`  *(mandatory)*
- **Behaviour:** reads the rep's free text, the LLM extracts every detail, and it **creates
  a brand-new interaction record** in PostgreSQL. Always a fresh row (never overwrites).
- **Uses AI for:** entity extraction + summarization.
- **Say:** *"Met Dr. Sharma, discussed OncoBoost efficacy, positive, shared brochure."*

### 2️⃣ `edit_interaction`  *(mandatory)*
- **Behaviour:** changes **one field** of the interaction currently on screen.
- **Say:** *"Change the sentiment to Neutral."*

### 3️⃣ `delete_interaction`
- **Behaviour:** **erases** by prompt — either one field (e.g. samples) or the whole record
  (`field="all"` clears the form and deletes the row).
- **Say:** *"Erase the samples distributed"* or *"Clear the form."*

### 4️⃣ `search_interactions`
- **Behaviour:** **looks up** past interactions from PostgreSQL, optionally by HCP name, and
  returns a short summary list. Does not change the current form.
- **Say:** *"Show my past interactions with Dr. Sharma."*

### 5️⃣ `suggest_followups`
- **Behaviour:** the **LLM generates** 2–4 concrete next-step suggestions from the current
  interaction and fills the "AI Suggested Follow-ups" section.
- **Say:** *"Suggest follow-ups for this interaction."*

| # | Tool | Job | Mandatory |
|---|------|-----|:---:|
| 1 | log_interaction | Extract + create new record | ✅ |
| 2 | edit_interaction | Modify one field | ✅ |
| 3 | delete_interaction | Erase field / whole record | ➕ |
| 4 | search_interactions | Find past records | ➕ |
| 5 | suggest_followups | AI-generated next steps | ➕ |

---

## 🔄 7. Main Project Flow

```
 [ User types/speaks on the right chat ]
                │
                ▼
 React + Redux  ──POST /api/chat──▶  FastAPI
                                        │
                                        ▼
                              LangGraph AGENT
                                        │  (send message + current form)
                                        ▼
                             Groq LLM (llama-3.3-70b)
                                        │  decides: which tool? what data?
                                        ▼
                       one of the 5 TOOLS runs
                                        │  save / read
                                        ▼
                                  PostgreSQL
                                        │
                                        ▼
        returns { reply, updated form_data, tools_used }
                │
                ▼
   Redux updates ▶ the LEFT form auto-fills (changed fields flash yellow)
```

Every step is decided by the **LLM + LangGraph** — this is what makes the project AI-first
and satisfies the "no hardcoded logic" requirement.

---

## 🐘 8. PostgreSQL — the database

- Each interaction is one row in the **`interactions`** table.
- **Columns:** `hcp_name, interaction_type, date, time, attendees, topics_discussed,
  materials_shared, samples_distributed, sentiment, outcomes, follow_up_actions,
  ai_suggested_followups, created_at, updated_at`.
- **SQLAlchemy** (ORM) is used; tables auto-create on startup ([`database.py`](backend/app/database.py),
  [`models.py`](backend/app/models.py)).
- The **search** tool reads from here; **log/edit/delete** write to here. Data survives app restarts.

---

## ⚛️ 9. Frontend explained

- **`components/LogInteractionScreen.jsx`** — the two-panel layout.
- **`components/InteractionForm.jsx`** — the LEFT form. All fields are **read-only** and
  render from Redux; changed fields **flash** to show the AI filled them.
- **`components/AIChatAssistant.jsx`** — the RIGHT chat; sends messages, shows replies and
  **tool chips** (which tool fired).
- **`components/VoiceNoteButton.jsx`** — 🎤 records voice (Web Speech API) → sends the
  transcript to the same agent.
- **`store/`** — Redux slices: `formSlice` (form data, auto-filled by the AI response),
  `chatSlice` (messages + the async call to the backend).

---

## 🐍 10. Backend explained

- **`app/main.py`** — FastAPI app; the `POST /api/chat` endpoint runs the agent and returns
  the reply + updated form + which tools fired.
- **`app/agent/graph.py`** — builds the LangGraph agent (nodes, edges, checkpointer).
- **`app/agent/tools.py`** — the 5 tools.
- **`app/agent/llm.py`** — the Groq LLM factory.
- **`app/models.py` / `app/database.py`** — PostgreSQL model + connection.
- **`app/config.py`** — reads settings from `.env`.

---

## 📁 11. Project structure

```
AIVOA/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI + /api/chat
│   │   ├── config.py          # env settings
│   │   ├── database.py        # PostgreSQL engine/session
│   │   ├── models.py          # Interaction table
│   │   ├── schemas.py         # request/response models
│   │   └── agent/
│   │       ├── llm.py         # Groq LLM factory
│   │       ├── tools.py       # the 5 LangGraph tools
│   │       └── graph.py       # LangGraph agent (StateGraph)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/        # Screen, Form, Chat, VoiceNote
│   │   ├── store/             # Redux: formSlice, chatSlice, store
│   │   ├── api.js
│   │   └── index.css          # Inter font, two-panel styling
│   └── package.json
├── docs/                      # voice script + interview Q&A (PDFs)
└── README.md
```

---

## 🚀 12. How to run

**Prerequisites:** Python 3.11+, Node.js 18+, PostgreSQL running, a free Groq key
(https://console.groq.com/keys).

**1. Database** — create it (tables auto-create on startup):
```sql
CREATE DATABASE hcp_crm;
```

**2. Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # then set GROQ_API_KEY + DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

**3. Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. (API docs: http://localhost:8000/docs)

---

## 💬 13. Try these prompts

| Goal | Type/speak in the AI Assistant |
|------|-------------------------------|
| **Log** | `Met Dr. Sharma, discussed OncoBoost Phase III efficacy, positive sentiment, shared brochure, gave 2 samples` |
| **Edit** | `Change the sentiment to Neutral` |
| **Erase** | `Erase the samples distributed` |
| **Search** | `Show my past interactions with Dr. Sharma` |
| **Follow-ups** | `Suggest follow-ups for this interaction` |
| **Voice** | Click 🎤 *Summarize from Voice Note*, speak, and the AI logs it |

---

## 🧩 14. Challenges faced & fixes

1. **Model decommissioned** — Groq removed `gemma2-9b-it`. → Switched to
   `llama-3.3-70b-versatile` (allowed by the assignment); model is a single env var.
2. **Concurrent form update error** — when the LLM called two tools in one step, both wrote
   `form_data` and LangGraph raised `InvalidUpdateError`. → Set `parallel_tool_calls=False`
   (one tool per turn) **and** added a **merge reducer** for `form_data`.
3. **New logs overwrote old ones** — because the form kept the previous record's `id`, a new
   "log" updated the old row. → `log_interaction` now always starts a **fresh record**, so
   each HCP is saved separately.

---

## ✅ 15. Conclusion

This project demonstrates a true **AI-first** workflow: the field rep only **talks**, and the
**LangGraph agent + Groq LLM** do all the work — logging, editing, deleting, searching, and
suggesting follow-ups — while every field is written to **PostgreSQL**. It fully honors the
mandatory stack (**LangGraph + an LLM**), uses **React + Redux** and **Python + FastAPI**, and
keeps **zero hardcoded logic** for the tools. The form is just a live mirror; the AI is the brain.