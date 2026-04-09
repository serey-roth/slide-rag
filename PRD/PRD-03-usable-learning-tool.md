# PRD 03 — Usable Learning Tool

**Status:** Superseded by PRD 04
**Version:** 0.3
**Date:** 2026-03-14

---

## Motivation

The long-term vision is a complete personal learning agent — one that knows your courses, your weak areas, and helps you learn both through and beyond your lecture material.

V1 and V2 established the foundation: RAG over slides, multi-agent routing, Q&A and quiz working together. That's the skeleton. V3 is about making the skeleton into a real tool.

Right now it's a POC you'd demo, not something you'd actually study with. The gaps are concrete: you can't see a diagram, you can't ask a question the slides don't answer, you can't pick up where you left off, and the CLI is too rough to use daily. Fix those four things and you have something genuinely useful.

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
- Q&A and quiz that can reference visual slide content
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
| --- | --- | --- |
| 1 | See slide images and formulas in answers | I understand visually-dense content |
| 2 | Ask questions that go beyond the slides | I can learn deeper than the lecturer wrote |
| 3 | Resume where I left off | I don't lose context between study sessions |
| 4 | Use a web interface | The tool is usable day-to-day, not just as a demo |

---

## Scope

**In:**

- Web UI (NiceGUI) with markdown, image, and formula rendering
- Ingest: slide image extraction, formula preservation
- Session memory across runs (chat history)
- Vision in Q&A and quiz — slide images included in context

**Out:**

- Learner model, spaced repetition, adaptive difficulty
- Calendar or portal integration
- Agent-to-agent communication
- Multi-user
- Question type expansion beyond MCQ (moved to V5)

---

## Build Sequence

1. Web UI — unblocks everything, ship first
2. Ingest: image extraction — PNG per slide, feed into retrieval
3. Formula rendering — LaTeX in UI, preservation in ingest
4. Vision in Q&A and quiz — include slide images in context when available
5. Session memory — persist conversations across runs

---

## Key Risks

| Risk | Mitigation |
| --- | --- |
| Formula extraction from PDFs is lossy | Flag math-heavy slides; preserve raw text layer |
| Beyond-slides mode produces ungrounded answers | Show "beyond slides" indicator clearly in UI when active |
