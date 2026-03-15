# PRD 03 — Usable Learning Tool

**Status:** Active
**Version:** 0.3
**Date:** 2026-03-14

---

## Motivation

The long-term vision is a complete personal learning agent — one that knows your courses, your schedule, your weak areas, and helps you learn both through and beyond your lecture material.

V1 and V2 established the foundation: RAG over slides, multi-agent routing, Q&A and quiz working together. That's the skeleton. V3 is about making the skeleton into a real tool.

Right now it's a POC you'd demo, not something you'd actually study with. The gaps are concrete: you can't see a diagram, you can't ask a question the slides don't answer, you can't pick up where you left off, and the CLI is too rough to use daily. Fix those four things and you have something genuinely useful — a study tool that works for your actual courses, not just the two PDFs you tested with.

---

## Problem

The V2 CLI works as a demo but fails as a daily study tool:

- No support for visual slides — diagrams, charts, and formulas are core to STEM courses but completely invisible to the system
- Locked to slide content — can't go deeper than what the lecturer wrote
- Every session starts cold — no memory of what was studied
- CLI makes the experience too friction-heavy for real use

---

## Goals

- Web UI that renders markdown, images, and formulas
- Ingest pipeline that extracts slide images and formulas alongside text
- Q&A and quiz that can go beyond slide content when slides are insufficient
- Multiple question types beyond MCQ
- Session memory persisted across runs

---

## Non-Goals

- Learner model / spaced repetition
- Student portal or calendar integration
- Agent-to-agent communication
- Adaptive difficulty
- Multi-user or auth
- Cross-deck knowledge graphs

---

## User Stories

| # | As a student, I want to... | So that... |
|---|---|---|
| 1 | See slide images and formulas in answers | I understand visually-dense content |
| 2 | Ask questions that go beyond the slides | I can learn deeper than the lecturer wrote |
| 3 | Get different question types, not just MCQ | I'm tested in ways that match the exam |
| 4 | Resume where I left off | I don't lose context between study sessions |
| 5 | Use a web interface | The tool is usable day-to-day, not just as a demo |

---

## Scope

**In:**
- Web UI (Streamlit for v3, FastAPI + React in v4)
- Ingest: slide image extraction, formula preservation
- Beyond-slides mode — toggle between slide-grounded and extended answers
- Question types: MCQ, true/false, fill-in-blank, free response
- Session memory across runs (conversations + quiz history)

**Out:**
- Learner model, spaced repetition, adaptive difficulty
- Calendar or portal integration
- Agent-to-agent communication
- Multi-user

---

## Build Sequence

1. Web UI — unblocks everything, ship first
2. Ingest: image extraction — PNG per slide, feed into retrieval
3. Beyond-slides mode — low effort, high value
4. Question type variety — true/false and fill-in-blank first, free response after
5. Session memory — persist conversations and quiz history
6. Formula rendering — LaTeX in UI, preservation in ingest
7. Vision in Q&A and quiz — include slide images in context when available

---

## Key Risks

| Risk | Mitigation |
|---|---|
| Formula extraction from PDFs is lossy | Flag math-heavy slides; preserve raw text layer |
| Free response grading is inconsistent | Strict rubric prompt; show raw model feedback to user |
| Beyond-slides mode produces ungrounded answers | Show "beyond slides" indicator clearly in UI when active |
| Streamlit limits complex interactions | Accept for v3; plan FastAPI migration for v4 |
