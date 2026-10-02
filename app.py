import asyncio
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from dotenv import set_key

from clients import Attachment, MODELS, MODEL_DISPLAY, call_claude, call_openai, reload_clients

app = FastAPI(title="AI Board")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── History (persisted to disk, survives app restarts) ───────────────
HISTORY_FILE = Path.home() / 'ai-board' / 'history.json'
MAX_SESSIONS = 100

def _read_history() -> List[Dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []

def _write_history(sessions: List[Dict]):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(sessions))

@app.get("/api/history")
async def get_history():
    return JSONResponse(_read_history())

@app.post("/api/history")
async def save_session(request: Request):
    session = await request.json()
    sessions = _read_history()
    sessions.insert(0, session)
    if len(sessions) > MAX_SESSIONS:
        sessions = sessions[:MAX_SESSIONS]
    _write_history(sessions)
    return JSONResponse({"ok": True})

@app.delete("/api/history/{session_id}")
async def delete_session(session_id: str):
    sessions = [s for s in _read_history() if s.get("id") != session_id]
    _write_history(sessions)
    return JSONResponse({"ok": True})

# ── API keys (stored in the same .env file main.py loads) ────────────
_ENV_CANDIDATES = (Path.home() / '.ai-board' / '.env', Path.home() / 'ai-board' / '.env')
ENV_PATH = next((p for p in _ENV_CANDIDATES if p.exists()), _ENV_CANDIDATES[0])
API_KEYS = {
    "ANTHROPIC_API_KEY": "Claude (Anthropic)",
    "OPENAI_API_KEY":    "ChatGPT (OpenAI)",
    "GOOGLE_API_KEY":    "Gemini (Google)",
    "XAI_API_KEY":       "Grok (xAI)",
}

@app.get("/api/keys")
async def get_keys():
    # Never return the keys themselves — just whether each is set and its last 4 chars.
    out = []
    for name, label in API_KEYS.items():
        v = os.environ.get(name, "")
        out.append({"name": name, "label": label, "set": bool(v), "hint": v[-4:] if len(v) >= 8 else ""})
    return JSONResponse(out)

@app.post("/api/keys")
async def update_keys(request: Request):
    body = await request.json()
    updates = {k: str(v).strip() for k, v in body.items() if k in API_KEYS and str(v).strip()}
    if updates:
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        ENV_PATH.touch(exist_ok=True)
        for k, v in updates.items():
            set_key(str(ENV_PATH), k, v)
            os.environ[k] = v
        ENV_PATH.chmod(0o600)
        reload_clients()
    return JSONResponse({"ok": True, "updated": list(updates)})

IMAGE_MIME_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "image/heic", "image/heif",
}


async def _process_upload(file: UploadFile) -> Attachment:
    """Read uploaded file, extracting text from PDFs."""
    data = await file.read()
    mime = (file.content_type or "application/octet-stream").split(";")[0].strip()
    name = file.filename or "file"

    is_pdf = mime == "application/pdf" or name.lower().endswith(".pdf")
    if is_pdf:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
            data = text.encode("utf-8")
            mime = "text/plain"
        except Exception as e:
            data = f"[PDF extraction failed: {e}]".encode()
            mime = "text/plain"

    return Attachment(filename=name, mime_type=mime, data=data)


async def _call(
    model_key: str, fn, prompt: str, atts: List[Attachment] = []
) -> Tuple[str, Optional[str], Optional[str]]:
    try:
        answer = await fn(prompt, atts)
        return model_key, answer, None
    except Exception as e:
        return model_key, None, str(e)


def _answers_block(answers: dict) -> str:
    return "\n\n".join(
        f"**{MODEL_DISPLAY[k]['name']} ({MODEL_DISPLAY[k]['org']})**: {v}"
        for k, v in answers.items()
    )


@app.get("/")
async def root():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.post("/api/ask")
async def ask(
    question: str = Form(...),
    files: List[UploadFile] = File(default=[]),
):
    async def stream():
        q = question.strip()
        if not q:
            yield f"event: error\ndata: {json.dumps({'message': 'Question cannot be empty'})}\n\n"
            return

        def emit(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        # Process attachments (if any)
        atts: List[Attachment] = []
        for file in files:
            if file and file.filename:
                att = await _process_upload(file)
                atts.append(att)
                yield emit("file_info", {
                    "filename": att.filename,
                    "kind": "image" if att.is_image else "text",
                })

        # ── Round 1: Initial answers ────────────────────────────────────────
        yield emit("phase", {"phase": "initial", "message": "Getting initial answers from all models…"})

        tasks = [
            asyncio.create_task(_call(k, v, q, atts))
            for k, v in MODELS.items()
        ]
        answers: dict = {}
        for coro in asyncio.as_completed(tasks):
            key, answer, error = await coro
            result = answer if answer else f"[Error: {error}]"
            answers[key] = result
            yield emit("model_answer", {"model": key, "answer": result})

        # ── Round 2: Critique ────────────────────────────────────────────────
        yield emit("phase", {"phase": "discussion", "message": "Models are now critiquing each other's answers…"})

        answers_block = _answers_block(answers)

        def make_critique_prompt(model_key: str) -> str:
            own = f"{MODEL_DISPLAY[model_key]['name']} ({MODEL_DISPLAY[model_key]['org']})"
            return (
                f'You are {own}. The following question was put to four AI models:\n\n'
                f'"{q}"\n\n'
                f"Here are all four responses (yours is labeled **{own}**):\n\n"
                f"{answers_block}\n\n"
                "Please critically evaluate all responses, including your own. "
                "For each, note: what it gets right, any gaps or errors, and how it compares to the others. "
                "Be specific, honest, and constructive."
            )

        # Pass image attachments to critique round so models can still see them;
        # for text attachments the content is already embedded in round-1 answers.
        critique_atts = [a for a in atts if a.is_image]

        critique_tasks = [
            asyncio.create_task(_call(k, v, make_critique_prompt(k), critique_atts))
            for k, v in MODELS.items()
        ]
        critiques: dict = {}
        for coro in asyncio.as_completed(critique_tasks):
            key, critique, error = await coro
            result = critique if critique else f"[Error: {error}]"
            critiques[key] = result
            yield emit("model_critique", {"model": key, "critique": result})

        # ── Round 3: Consolidation ───────────────────────────────────────────
        yield emit("phase", {"phase": "consolidation", "message": "Synthesising the board discussion into a final answer…"})

        critiques_block = "\n\n".join(
            f"**{MODEL_DISPLAY[k]['name']}'s analysis**: {v}"
            for k, v in critiques.items()
        )
        consolidation_prompt = (
            f'You are the chair of a panel of AI experts. The panel was asked:\n\n"{q}"\n\n'
            f"The panel members gave these initial answers:\n\n{answers_block}\n\n"
            f"They then each provided a critical analysis:\n\n{critiques_block}\n\n"
            "Your task: write a single, authoritative consolidated answer that:\n"
            "1. Synthesises the best insights from all panel members\n"
            "2. Resolves any contradictions, explaining the reasoning\n"
            "3. Is well-structured and directly answers the question\n"
            "4. Clearly flags any genuine areas of uncertainty or ongoing debate\n\n"
            "Write the answer directly — no meta-commentary about the process."
        )

        try:
            consolidated = await call_claude(consolidation_prompt)
        except Exception:
            try:
                consolidated = await call_openai(consolidation_prompt)
            except Exception as e:
                consolidated = f"[Consolidation failed: {e}]"

        yield emit("consolidated", {"answer": consolidated})
        yield emit("done", {})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
