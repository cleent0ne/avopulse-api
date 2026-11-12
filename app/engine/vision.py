import os
import asyncio
import json
import base64
import httpx
from typing import Dict, Any, List, Optional
from app.engine.cache import lookup_cache

# ── API keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Shared prompt ─────────────────────────────────────────────────────────────
PROMPT = """You are an AFA-trained avocado maturity grader in Kenya.
Analyze the photo(s) of a freshly cut Hass avocado cross-section.
Return strictly a valid JSON object with the following schema:
{
  "flesh_colour_score": <float between 0.0 and 1.0, where 0.0 is pale watery green/immature and 1.0 is rich buttery yellow>,
  "seed_coat_colour": <one of "white", "tan", "brown">,
  "visual_band": <one of "below target", "borderline", "likely at or above 23%">,
  "visible_defects": [<list of defect strings, or empty>],
  "reasons": [<2 or 3 concise, plain-language bullet strings describing flesh pigmentation, seed coat detachment, and lipid accumulation>]
}
Do not wrap your answer in markdown ticks. Return raw JSON only."""


def _parse_ai_response(parsed: dict) -> Dict[str, Any]:
    """Normalise raw AI JSON into our standard result dict."""
    return {
        "source": "live",
        "visual_score": float(parsed.get("flesh_colour_score", 0.7)),
        "seed_coat_color": str(parsed.get("seed_coat_colour", "tan")),
        "visual_band": str(parsed.get("visual_band", "borderline")),
        "reasons": parsed.get("reasons", []),
    }


# ── Gemini Vision (primary) ───────────────────────────────────────────────────
async def _call_gemini(photos: List[bytes]) -> Optional[Dict[str, Any]]:
    """
    Call Gemini 1.5 Flash via REST with base64-encoded images.
    Returns parsed result dict or None on failure.
    """
    if not GEMINI_API_KEY or not photos:
        return None

    # Build multipart content parts
    parts = []
    for img_bytes in photos[:2]:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64,
            }
        })
    parts.append({"text": PROMPT})

    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 512,
        }
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-flash-lite-latest:generateContent?key={GEMINI_API_KEY}"
    )

    try:
        async with asyncio.timeout(20.0):
            async with httpx.AsyncClient(timeout=18.0) as client:
                res = await client.post(url, json=body)
                if res.status_code != 200:
                    return None
                data = res.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                # Strip markdown fences if model wrapped output
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                parsed = json.loads(text)
                result = _parse_ai_response(parsed)
                result["source"] = "gemini"
                return result
    except Exception:
        return None


# ── OpenRouter Vision (tertiary fallback) ─────────────────────────────────────
async def _call_openrouter(photos: List[bytes]) -> Optional[Dict[str, Any]]:
    """
    Call OpenRouter with google/gemini-flash-1.5 (vision-capable, free tier).
    Falls back to anthropic/claude-3-haiku if that fails.
    Returns parsed result dict or None.
    """
    if not OPENROUTER_API_KEY or not photos:
        return None

    # Build OpenAI-compatible messages with base64 image URLs
    image_parts = []
    for img_bytes in photos[:2]:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        image_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })
    image_parts.append({"type": "text", "text": PROMPT})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://avopulse.app",
        "X-Title": "AvoPulse Maturity Grading",
    }

    # Try vision-capable models in order
    models = [
        "google/gemini-flash-1.5",
        "anthropic/claude-3-haiku",
        "openai/gpt-4o-mini",
    ]

    for model in models:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": image_parts}],
            "max_tokens": 512,
            "temperature": 0.1,
        }
        try:
            async with asyncio.timeout(20.0):
                async with httpx.AsyncClient(timeout=18.0) as client:
                    res = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    if res.status_code != 200:
                        continue
                    data = res.json()
                    text = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    # Strip markdown fences
                    if text.startswith("```"):
                        text = text.split("```")[1]
                        if text.startswith("json"):
                            text = text[4:]
                    parsed = json.loads(text)
                    result = _parse_ai_response(parsed)
                    result["source"] = f"openrouter/{model}"
                    return result
        except Exception:
            continue

    return None


# ── Anthropic Claude Vision (secondary fallback) ──────────────────────────────async def _call_anthropic(photos: List[bytes]) -> Optional[Dict[str, Any]]:
    """
    Call Claude claude-sonnet-5-5 via REST. Returns parsed result or None.
    """
    if not ANTHROPIC_API_KEY or not photos:
        return None

    content_blocks = []
    for b in photos[:2]:
        b64_data = base64.b64encode(b).decode("utf-8")
        content_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64_data,
            }
        })
    content_blocks.append({"type": "text", "text": PROMPT})

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-5-5",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": content_blocks}],
    }

    try:
        async with asyncio.timeout(5.0):
            async with httpx.AsyncClient(timeout=4.5) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=body,
                )
                if res.status_code != 200:
                    return None
                data = res.json()
                text = data["content"][0]["text"].strip()
                parsed = json.loads(text)
                return _parse_ai_response(parsed)
    except Exception:
        return None


# ── Public entry point ────────────────────────────────────────────────────────
async def analyze_visual(
    photos: List[bytes],
    filenames: List[str] = None,
    live_ai: bool = True,
) -> Dict[str, Any]:
    """
    Analyse avocado cross-section photos.

    Priority chain:
      1. Gemini 1.5 Flash (primary live AI)
      2. Claude claude-sonnet-5-5 (secondary, only if Anthropic key set)
      3. Pre-cached deterministic engine (always available)

    If live_ai is False or no photos supplied, goes straight to cache.
    """
    if not live_ai or not photos:
        cached = lookup_cache(
            photos[0] if photos else b"",
            filenames[0] if filenames else None,
        )
        return {
            "source": "cached",
            "visual_score": cached["visual_score"],
            "seed_coat_color": cached["seed_coat_color"],
            "visual_band": cached["band"],
            "reasons": cached["reasons"],
        }

    # 1 — Try Gemini
    result = await _call_gemini(photos)
    if result:
        return result

    # 2 — Try Claude (optional)
    result = await _call_anthropic(photos)
    if result:
        return result

    # 3 — Try OpenRouter (gemini-flash-1.5 → claude-3-haiku → gpt-4o-mini)
    result = await _call_openrouter(photos)
    if result:
        return result

    # 4 — Deterministic cache fallback
    cached = lookup_cache(
        photos[0] if photos else b"",
        filenames[0] if filenames else None,
    )
    return {
        "source": "cached",
        "visual_score": cached["visual_score"],
        "seed_coat_color": cached["seed_coat_color"],
        "visual_band": cached["band"],
        "reasons": cached["reasons"],
    }
