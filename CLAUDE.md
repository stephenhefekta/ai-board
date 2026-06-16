# AI Board

A macOS desktop app that sends a question to Claude, ChatGPT, Gemini, and Grok in parallel, runs a cross-critique round, then synthesises a consolidated answer.

## Stack
- **Backend**: FastAPI + uvicorn (`app.py`)
- **AI clients**: `clients.py` — Anthropic, OpenAI, Google GenAI, xAI (Grok)
- **Frontend**: Single-page HTML/JS (`static/index.html`) with Tailwind + marked.js via CDN
- **Desktop**: `main.py` starts the server in a background thread, opens it in a native macOS WKWebView window via pywebview
- **Build**: `bash build.sh` → `dist/AI Board.app` (PyInstaller)

## Key files
- `app.py` — FastAPI routes, 3-round streaming pipeline (answers → critiques → consolidation)
- `clients.py` — API wrappers + model registry (`MODELS`, `MODEL_DISPLAY`)
- `main.py` — app entry point (server thread + pywebview window)
- `build.sh` — generates icon, runs PyInstaller
- `make_icon.py` — generates `AI Board.icns` from code (4 coloured dots on dark bg)

## API keys
Loaded from `~/.ai-board/.env` (gitignored; legacy `~/ai-board/.env` still works as a fallback). Required keys:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `XAI_API_KEY`

## Models (overridable via env)
- Claude: `claude-sonnet-4-6`
- ChatGPT: `gpt-4o`
- Gemini: `gemini-2.5-flash`
- Grok: `grok-3`

## Build & run
```bash
# Run in dev (no .app needed)
uvicorn app:app --reload

# Build .app
bash build.sh
# Output: dist/AI Board.app
```

---

# Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

> Source: https://github.com/forrestchang/andrej-karpathy-skills

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
