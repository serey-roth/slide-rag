# Learning Agent

A multi-agent study tool that answers questions and generates quizzes from your lecture slides. Retrieval is visual — slides are embedded as images so answers are grounded in diagrams, equations, and figures, not just extracted text.

## How it works

**Ingest** converts each PDF deck into slide images and builds a visual index using [ColPali](https://huggingface.co/vidore/colpali) patch embeddings. It then runs a comprehension pass with Claude to extract key topics and a one-sentence summary for each deck.

**Chat** retrieves the most relevant slides for your question (visually, via ColPali), passes them to Claude alongside a flat dump of your topic progress notes, and streams a grounded answer with slide citations. After each exchange, a local Ollama model writes a short progress note for any matched topics.

**Quiz** lets you pick topics from the deck's subject map, then generates MCQs grounded in the relevant slides. Progress notes for the selected topics are passed as context so Claude can focus on gaps. Quiz results are evaluated by Ollama and written back to the topic record.

Topic progress notes accumulate across sessions in `data/learner_model.json`. They feed context into chat and quiz, but there's no adaptive logic — it's context injection.

## Agents

| Agent | Model | Role |
| --- | --- | --- |
| Comprehension | Claude (Anthropic) | Extracts topics and summary from a deck on ingest |
| Chat | Claude (Anthropic) | Conversational Q&A grounded in slide images |
| Quiz | Claude (Anthropic) | Generates MCQs from selected topics and slides |
| Evaluator | Ollama llama3.2:3b | Writes progress notes from chat questions and quiz results |
| Resolver | Ollama nomic-embed-text | Matches free-text queries to known topic names |

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set your API key**

   ```bash
   echo "ANTHROPIC_API_KEY=sk-..." > .env
   ```

3. **Start Ollama** (required for the evaluator and topic resolver)

   ```bash
   ollama serve
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```

4. **Add your slides**

   Drop PDF slide decks into `data/decks/`.

5. **Ingest**

   ```bash
   python -m src.ingest
   ```

   Converts slides to images, builds the ColPali index, and runs the comprehension pass. Re-run whenever you add new decks.

6. **Run**

   ```bash
   python -m src.app
   ```

   Opens at `http://localhost:8080`.

## Usage

- **Home** — deck summaries and topic coverage
- **Chat** — ask questions in natural language; answers cite specific slides; topic nudges appear at session start
- **Quiz** — pick topics from a deck's subject map, take an MCQ quiz, review missed questions

## Requirements

- Python 3.11+
- Anthropic API key in `.env` as `ANTHROPIC_API_KEY`
- [Ollama](https://ollama.com) running locally with `nomic-embed-text` pulled
