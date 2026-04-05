# PRD 05 — Active Assessment

**Status:** Draft
**Version:** 0.1
**Date:** 2026-04-02

---

## Motivation

V4 closes the loop between learning and self-testing for MCQ. But multiple choice is the weakest form of assessment — it tests recognition, not recall or application. A student who can identify the right answer when shown it is not the same as a student who can derive it.

The next step is assessment that requires the student to produce an answer: explain a concept in their own words, solve a word problem, write code. These question types reveal gaps that MCQ hides. They also generate richer signal for the learner model — a wrong explanation tells you something, a correct one with good reasoning tells you more.

The evaluator is the enabling piece. Once you can grade free-form answers against slide content, you can build any question type on top of it and feed the results back into the chat agent.

---

## Problem

MCQ tests whether a student can recognize a correct answer. It doesn't test whether they can explain, apply, or produce. A student can pass every MCQ and still not understand the material well enough to use it.

Word problems, derivations, and coding tasks are where real understanding shows up. The current system can't generate them and can't grade them. Quiz and chat are also disconnected — wrong answers disappear instead of feeding back into learning.

---

## Goals

- Connect quiz outcomes back to chat so wrong answers drive deeper exploration
- Expand quiz question types to include word problems, math problems, and coding problems
- Grade open-ended answers with an LLM evaluator grounded in slide content
- Feed evaluation outcomes back into the learner model and chat agent
- Support Jupyter notebook execution for coding problems
- Map connections and gaps across multiple decks

---

## Non-Goals

- Adaptive quiz difficulty
- Spaced repetition scheduling
- Multi-user
- External content beyond uploaded slides (V6)

---

## User Stories

| # | As a student, I want to... | So that... |
| --- | --- | --- |
| 1 | Have wrong quiz answers feed into the conversation | I can explore what I got wrong without switching modes |
| 2 | Answer word problems derived from my slides | I practice applying concepts, not just recognizing them |
| 3 | Solve math problems and get graded feedback | I know whether my reasoning is correct, not just my answer |
| 4 | Write and run code against a coding problem | I get execution feedback, not just text feedback |
| 5 | Have wrong answers explained by the tutor | I understand why I was wrong, not just that I was |
| 6 | See how concepts connect across my decks | I build a unified picture of the subject, not isolated islands |

---

## Scope

**In:**

- Quiz → chat handoff — wrong answers carry question context into chat; tutor can unpack them naturally
- Open-ended evaluator agent — grades free-text answers against expected answer and slide context; produces a structured result (correct / partial / wrong + why)
- Word problems — generated from slide content, graded by the evaluator
- Math problems — generated and graded; LaTeX rendering already in place
- Coding problems — generated as prompts, graded by the evaluator (static analysis first, execution second)
- Jupyter execution environment — sandboxed kernel for coding problem submissions; results fed back into grading
- Cross-deck comprehension pass — maps connections and conflicts across multiple uploaded decks; surfaces in the learner model

**Out:**

- Adaptive difficulty
- Spaced repetition
- Multi-user
- External web search / research agent (V6)

---

## Architecture

**Open-ended evaluator** — a new agent distinct from the existing `evaluator.py` (which tracks topic progress from chat). Takes a question, the student's answer, the expected answer, and relevant slide context. Returns a structured result: verdict (correct / partial / wrong), reasoning, and a short explanation for the student. Writes outcome to the learner model.

**Question generator** — extends the existing quiz agent to produce word problems, math problems, and coding prompts. Each type has its own generation prompt; all are grounded in retrieved slide content.

**Jupyter executor** — a sandboxed kernel process. Coding problem submissions are executed; stdout, stderr, and test results are returned to the evaluator as additional grading context.

**Cross-deck comprehension** — a pass that runs after two or more decks are ingested. Reads the subject maps already in the learner model, identifies concept overlap and dependency, and writes a cross-deck summary. Surfaces in the chat agent when the student asks about connections.

The evaluator is the connective tissue — every non-MCQ question type routes through it, and its output writes to the learner model and optionally seeds the chat context.

---

## Build Sequence

1. Quiz → chat handoff — smallest scope, highest immediate value; no new agents required
2. Open-ended evaluator — foundation for all non-MCQ question types
3. Word problems — first new question type; text in, text out, evaluator grades
4. Math problems — same flow, LaTeX already handled in the UI
5. Cross-deck comprehension — independent of question types; can ship in parallel
6. Coding problems (static) — code in, evaluator grades without execution
7. Jupyter execution — live execution results fed into the evaluator

---

## Key Risks

| Risk | Mitigation |
| --- | --- |
| Evaluator is inconsistent or too harsh/lenient | Ground scoring in slide content; test with known-correct and known-wrong answers |
| Word/math problem generation drifts from slide content | Retrieval must gate generation; reject problems with no grounding source |
| Jupyter execution is a sandbox escape risk | Strict kernel isolation; no network, no filesystem writes outside a temp dir |
| Cross-deck connections are hallucinated | Ground connections in explicit concept overlap, not inference; require citation |
| Evaluator results feel punitive without explanation | Always return the why alongside the verdict; tie to chat for exploration |
