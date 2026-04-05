# PRD 04 — Learner Model & Context-Aware Tutor

**Status:** Complete
**Version:** 0.6
**Date:** 2026-04-02

---

## Motivation

V1 through V3 built a capable retrieval and generation system — you can ask questions, get cited answers, and take quizzes grounded in your slides. But every session starts cold. The system has no memory of what you've studied, no understanding of what a deck is about before you ask, and no way to tailor responses to where you actually are.

V4 adds memory and comprehension. When you upload a deck the system reads it and builds a subject map. As you chat and quiz, it tracks what you've covered. That context flows into every response. The system still waits for you to ask — but when you do, it knows who it's talking to.

---

## Problem

The system treats every session as a blank slate. It has no model of the subject and no model of you. A student who has studied half the deck gets the same responses as one who hasn't opened it. Quiz questions don't account for what you already know. The comprehension work happens at query time, not at upload time.

---

## Goals

- Build a subject map from every uploaded deck automatically
- Maintain a learner model updated by every chat and quiz interaction
- Use the learner model to inform chat and quiz responses
- Surface topic suggestions based on what the student hasn't covered yet

---

## Non-Goals

- True proactive initiation — the system does not start conversations or push recommendations unprompted (deferred to V5)
- Calendar or course schedule integration
- Multi-user or auth
- Cloud sync or cross-device persistence
- External content beyond uploaded slides

---

## User Stories

| # | As a student, I want to... | So that... |
| --- | --- | --- |
| 1 | Have the system understand a deck when I upload it | I don't have to explain what it covers before asking questions |
| 2 | Get answers that account for what I've already studied | I'm not re-explained things I know |
| 3 | See topic suggestions when I open chat | I have a starting point even when I don't know what to ask |
| 4 | Have the system remember what I've covered across sessions | I pick up where I left off, not from scratch |

---

## Scope

**In:**

- Comprehension agent — runs on upload; extracts key concepts and a summary; writes a subject map to the learner model
- Learner model — tracks topics, progress notes, and last-seen timestamps per deck; persisted across sessions
- Upload as trigger — comprehension fires automatically after ingest completes
- Context-aware chat — learner model passed as context to the chat agent; responses informed by what the student has covered
- Context-aware quiz — learner model progress notes passed to the quiz agent; questions account for prior exposure
- Topic nudges — unseen and weak topics surfaced as suggestions at chat session start

**Out:**

- Proactive initiation — system starting conversations, pushing learning briefs, or recommending topics unprompted (V5)
- Quiz → chat handoff (V5)
- Cross-deck comprehension pass (V5)
- Question type expansion (V5)
- Open-ended answer evaluator (V5)
- Research agent / external web search (V5)
- Learner model exposed as a UI view (internal only for now)
- Adaptive quiz difficulty
- Spaced repetition
- Multi-user

---

## Architecture

Three agents, one shared learner model:

**Comprehension agent** — triggered on upload. Reads the full deck, extracts key concepts and a one-line summary, writes the subject map to the learner model.

**Chat agent** — reactive conversational surface. Receives the learner model as context so responses are tailored to what the student has and hasn't covered. Writes topic exposure back to the learner model after each exchange.

**Quiz agent** — generates MCQ assessments grounded in the subject map. Receives learner model progress notes so questions can account for prior study. Writes outcomes to the learner model.

The learner model is the connective tissue — shared state that all three read from and write to. Persisted to disk between sessions.

---

## Build Sequence

1. ✅ Learner model — data structure and persistence; the foundation everything else reads and writes
2. ✅ Comprehension agent — upload trigger, subject map extraction, learning brief written to learner model
3. ✅ Context-aware chat and quiz — learner model context passed to both agents
4. ✅ Topic nudges — unseen topics surfaced as clickable suggestions at chat session start

---

## Key Risks

| Risk | Mitigation |
| --- | --- |
| Comprehension brief is generic, not useful | Prompt must produce opinionated output — not a summary, a study plan |
| Learner model grows stale or contradictory | Version entries with timestamps; recency-weight when reading |
| Topic nudges feel random, not prioritised | Weight unseen topics over seen; surface highest-priority gaps first |
