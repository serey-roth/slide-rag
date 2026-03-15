# PRD 01 — Slide Q&A

**Status:** Superseded by PRD 02
**Version:** 0.1
**Date:** 2026-03-06

---

## Problem

University slide decks are dense and semantically incomplete by design — they assume a lecturer is filling in the gaps live. Studying from them is slow and fragmented. There is no way to ask a natural language question and get a grounded, cited answer from the slides themselves.

Existing tools (SlideSpeak, StudyFetch, Microsoft Copilot) are black boxes, not tuned for deep Q&A, and do not address the core problem: **slides are compressed speech, not self-contained documents**.

---

## Goals

- Ask natural language questions against slide decks and get cited answers
- Answers grounded in specific slides, with slide citations
- Supplement sparse slides with LLM-generated context at query time
- Support semantic search across a full deck (up to 150 slides)
- Single user, local only — data stays on disk

---

## Non-Goals

- Image, diagram, or chart understanding
- Quiz or flashcard mode
- Cross-deck relationship graphs
- Multi-user or cloud deployment
- Ingest-time enrichment

---

## User Stories

| # | As a student, I want to... | So that... |
|---|---|---|
| 1 | Ask a question in natural language | I get a direct answer without manually searching slides |
| 2 | See which slide(s) the answer came from | I can verify and read the original context |
| 3 | Get a clear explanation even when the slide is sparse | I understand the concept, not just the bullet |
| 4 | Search across all slides in a deck | I can find relevant content I forgot was in the deck |
| 5 | Add a new deck and query it immediately | I don't have to wait or reconfigure anything |

---

## Scope

**In:**
- Natural language Q&A over PDF slide decks
- Hybrid retrieval (semantic + keyword) with cited answers
- Sparse slide handling — LLM supplements incomplete slides inline
- Stateful conversation memory within a session (last 6 turns)
- Single deck or multi-deck selection at session start

**Out:**
- Images, formulas, OCR
- Quiz / testing mode
- Session persistence across runs
- Cross-deck knowledge graphs
- Multi-user

---

## Key Risks

| Risk | Mitigation |
|---|---|
| Sparse slides produce low-quality answers | LLM supplements gaps inline; prompt constrains it to not fabricate |
| Retrieval misses the right slide | Sliding window adds adjacent slides as context |
| Missing visual content (diagrams, math) | Accepted V1 limitation |
