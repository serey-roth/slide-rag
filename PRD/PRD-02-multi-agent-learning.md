# PRD 02 — Multi-Agent Learning System

**Status:** Superseded by PRD 03
**Version:** 0.2
**Date:** 2026-03-13

---

## Motivation

V1 answered questions from slides passively. A student who only asks questions learns less than one who is also tested. Retrieval alone is not learning — it's search. V2 adds active learning: the system tests you, evaluates your answers, and explains what you got wrong.

---

## Problem

V1 had no way to assess understanding. A student could read answers indefinitely without knowing whether they actually understood the material. There was also no way to ask a follow-up question after a wrong answer without losing quiz context.

---

## Goals

- Route user intent automatically to the right agent (Q&A or quiz)
- Generate grounded quiz questions from retrieved slides
- Provide explanations for wrong answers grounded in slide content
- Allow natural Q&A mid-quiz without losing context
- Maintain conversation history across the session

---

## Non-Goals

- Image or formula understanding
- Summary agent
- Session persistence across runs
- Spaced repetition or learner model
- Web UI
- Multi-user

---

## User Stories

| # | As a student, I want to... | So that... |
| --- | --- | --- |
| 1 | Ask a question and get a cited answer | I understand a concept without searching manually |
| 2 | Request a quiz on a topic | I'm tested on what I need to study |
| 3 | Get questions grounded in actual slide content | Questions are relevant, not generic |
| 4 | Get an explanation when I answer wrong | I know what I got wrong and why |
| 5 | Ask a clarifying question after a wrong answer | I can understand before moving on |
| 6 | See my score at the end | I know where I stand |

---

## Scope

**In:**

- Orchestrator that classifies user intent (Q&A, quiz, quit)
- Q&A agent — retrieval + streaming answer + citations
- Quiz agent — batch question generation + interactive loop + score
- Post-wrong-answer explanation via Q&A agent
- Shared conversation history across Q&A and quiz explanations
- Context-aware intent classification using recent user queries

**Out:**

- Image/formula support
- Quiz session persistence
- Learner model or weak-area tracking
- Adaptive difficulty
- Web UI

---

## Key Risks

| Risk | Mitigation |
| --- | --- |
| Quiz questions are off-topic or hallucinated | Retrieval-grounded generation; strict format prompt |
| Intent misclassified (quiz vs Q&A) | Recent query history passed to orchestrator for context resolution |
| No visual content in questions | Accepted V2 limitation — text-only slides only |
