import asyncio
import base64
import os
from dataclasses import dataclass
from typing import Optional, List

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from google import genai as google_genai
from google.genai import types as genai_types


# --- Attachment ---

@dataclass
class Attachment:
    filename: str
    mime_type: str
    data: bytes

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith('image/')

    @property
    def b64(self) -> str:
        return base64.b64encode(self.data).decode()

    @property
    def text_content(self) -> str:
        return self.data.decode('utf-8', errors='replace')


def _text_prompt(prompt: str, atts: List[Attachment]) -> str:
    """Prepend text-file content to the prompt."""
    text_atts = [a for a in atts if not a.is_image]
    if text_atts:
        parts = "\n\n".join(f"[Attached file: {a.filename}]\n\n{a.text_content}" for a in text_atts)
        return f"{parts}\n\n---\n\n{prompt}"
    return prompt


# --- Clients ---

claude_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
grok_client = AsyncOpenAI(
    api_key=os.environ.get("XAI_API_KEY", ""),
    base_url="https://api.x.ai/v1",
)
gemini_client = google_genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", ""))

# --- Model names (overridable via env) ---

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GROK_MODEL   = os.environ.get("GROK_MODEL",   "grok-3")

MAX_TOKENS = 8192


# --- Callers ---

async def call_claude(prompt: str, atts: List[Attachment] = []) -> str:
    image_atts = [a for a in atts if a.is_image]
    full_prompt = _text_prompt(prompt, atts)
    if image_atts:
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": a.mime_type, "data": a.b64},
            }
            for a in image_atts
        ] + [{"type": "text", "text": full_prompt}]
    else:
        content = full_prompt

    message = await claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
    )
    return message.content[0].text


async def call_openai(prompt: str, atts: List[Attachment] = []) -> str:
    image_atts = [a for a in atts if a.is_image]
    full_prompt = _text_prompt(prompt, atts)
    if image_atts:
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{a.mime_type};base64,{a.b64}"}}
            for a in image_atts
        ] + [{"type": "text", "text": full_prompt}]
    else:
        content = full_prompt

    response = await openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
    )
    return response.choices[0].message.content


async def call_gemini(prompt: str, atts: List[Attachment] = []) -> str:
    image_atts = [a for a in atts if a.is_image]
    full_prompt = _text_prompt(prompt, atts)
    if image_atts:
        contents = [
            genai_types.Part.from_bytes(data=a.data, mime_type=a.mime_type)
            for a in image_atts
        ] + [genai_types.Part.from_text(text=full_prompt)]
    else:
        contents = full_prompt

    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model=GEMINI_MODEL,
        contents=contents,
        config=genai_types.GenerateContentConfig(max_output_tokens=MAX_TOKENS),
    )
    return response.text


async def call_grok(prompt: str, atts: List[Attachment] = []) -> str:
    image_atts = [a for a in atts if a.is_image]
    full_prompt = _text_prompt(prompt, atts)
    if image_atts:
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{a.mime_type};base64,{a.b64}"}}
            for a in image_atts
        ] + [{"type": "text", "text": full_prompt}]
    else:
        content = full_prompt

    response = await grok_client.chat.completions.create(
        model=GROK_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
    )
    return response.choices[0].message.content


# --- Registry ---

MODELS = {
    "claude":  call_claude,
    "chatgpt": call_openai,
    "gemini":  call_gemini,
    "grok":    call_grok,
}

MODEL_DISPLAY = {
    "claude":  {"name": "Claude",  "org": "Anthropic", "color": "#D97706", "bg": "#FFFBEB", "border": "#FCD34D", "text": "#78350F"},
    "chatgpt": {"name": "ChatGPT", "org": "OpenAI",    "color": "#059669", "bg": "#ECFDF5", "border": "#6EE7B7", "text": "#064E3B"},
    "gemini":  {"name": "Gemini",  "org": "Google",    "color": "#2563EB", "bg": "#EFF6FF", "border": "#93C5FD", "text": "#1E3A8A"},
    "grok":    {"name": "Grok",    "org": "xAI",       "color": "#7C3AED", "bg": "#F5F3FF", "border": "#C4B5FD", "text": "#4C1D95"},
}
