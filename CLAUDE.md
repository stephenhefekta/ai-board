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
Loaded from `~/ai-board/.env` (gitignored). Required keys:
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
