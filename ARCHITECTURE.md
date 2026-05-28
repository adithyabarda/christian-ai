# ChristianAI Assistant — Architecture Note

## Overview

ChristianAI is a scripture-grounded, denomination-aware Christian AI assistant
that combines conversational AI, safety moderation, hallucination prevention,
and free image generation in a single Streamlit web app.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit (Python) |
| Chat / Reasoning | Gemini 2.5 Flash (Google GenAI SDK) |
| Image Generation | Pollinations.ai — FLUX model (free, no API key) |
| Safety | Custom rule-based moderation pipeline |
| Scripture Validation | Custom regex + 66-book canon database |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Streamlit UI  (app.py)                  │
│        Chat Tab │ Image Tab │ Evaluation Tab             │
└──────┬──────────────────┬───────────────────────────────┘
       │                  │
       ▼                  ▼
┌─────────────┐    ┌─────────────────────────────────────┐
│moderation.py│    │           config.py                  │
│ ─────────── │    │  CHAT_MODEL : gemini-2.5-flash       │
│ Input check │    │  IMAGE API  : pollinations.ai/FLUX   │
│ Output check│    │  SYSTEM_PROMPT (9 rules)             │
│ Fake verse  │    │  DENOMINATION_PROMPTS (9 traditions) │
│ detection   │    └─────────────────────────────────────┘
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│              bible_grounding.py                          │
│  Regex scan → 66-book validation → local verse DB lookup │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────┐    ┌──────────────────────────┐
│  Gemini 2.5 Flash    │    │  Pollinations.ai (FLUX)  │
│  (Text / Chat)       │    │  (Image Generation)      │
│  google-genai SDK    │    │  Free HTTP GET request   │
└──────────────────────┘    └──────────────────────────┘
```

---

## Key Engineering Decisions

### 1. Two-Pass Moderation
Every user message is checked by rule-based regex patterns **before** the AI
sees it, and the AI response is checked again **before** the user sees it.
This catches harmful content at both ends — even if the model generates it.

Categories blocked: hate speech, Satanic prayer rewrites, fake scripture
generation, self-harm, sexual content involving sacred figures.

### 2. Scripture Grounding & Hallucination Prevention
The most common failure in religious AI is fabricated Bible verses.
Every AI response is scanned with a regex for patterns like `John 3:16`.
Each reference is then:
- Validated against a 66-book canon DB (with per-book chapter limits)
- Checked against a local known-verse database (15 common verses)
- Flagged to the user if structurally invalid

A misquote dictionary also catches 7 famous non-Bible phrases at input time
(e.g. "God helps those who help themselves", "the lion and the lamb").

### 3. Denomination-Aware Prompting
9 Christian traditions supported. Each injects a denomination-specific
context block into the system prompt — e.g. Catholic users get Magisterium
and transubstantiation framing; Orthodox users get Theosis and Divine Liturgy.

### 4. Free Image Generation (No API Key)
Instead of paid image APIs, the app uses Pollinations.ai — a free public
endpoint powered by FLUX. No token, no signup, no billing. Just an HTTP GET
request that returns a PNG image directly.

### 5. Persistent Conversation Memory
Streamlit session state holds the full Gemini chat history as a list of
`Content` objects. This gives the model true multi-turn memory without
re-sending the entire conversation manually each time.

---

## Safety Architecture (Flow)

```
User Input
    │
    ▼
[1] Hard Block Patterns (hate, Satan rewrites, explicit) ──► BLOCKED ✅
    │
    ▼
[2] Direct Phrase List (14 exact blocked phrases) ──────► BLOCKED ✅
    │
    ▼
[3] Soft Patterns — strict mode only ───────────────────► BLOCKED ✅
    │
    ▼
[4] Fake Verse + Misquote Detection ────────────────────► WARNING ⚠️
    │
    ▼
[5] Gemini System Prompt (9 safety rules baked in)
    │
    ▼
[6] Output Moderation (same hard patterns on AI response)
    │
    ▼
[7] Scripture Validation (flag invalid refs in response)
    │
    ▼
Display to User (with warnings / verse citations)
```

---

## File Structure

```
christian_ai_assistant/
├── app.py                  # Streamlit UI + orchestration (3 tabs)
├── config.py               # Models, system prompt, denomination prompts
├── moderation.py           # Input/output safety + fake verse detection
├── bible_grounding.py      # 66-book canon DB, verse regex, hallucination flagging
├── evaluation_dataset.py   # 20+ adversarial & edge-case test cases
├── ARCHITECTURE.md         # This document
├── README.md               # Setup instructions
└── requirements.txt        # Python dependencies
```

---

## Hallucination Prevention Summary

| Risk | Mitigation |
|---|---|
| Fabricated scripture | Verse regex + 66-book canon validation |
| Non-existent Bible books | Book whitelist with chapter count limits |
| Implausible verse numbers | Per-book chapter limits enforced |
| Common misquotes at input | 7-phrase misquote dictionary |
| Historical fabrication | System prompt enforces explicit uncertainty |
| Theological overconfidence | Prompt enforces "present multiple views" |
| Satanic/blasphemous rewrites | Dedicated regex + direct phrase blocklist |
