# ai_tutor.py
# ============================================================
# ✅ Hotena AI Tutor (하테나쌤) - low cost, short answers
# - Default model: gpt-4o-mini (override via OPENAI_MODEL_LOW)
# - Cache: 1~5 minutes (TTL via AI_CACHE_TTL_SEC)
# - Context: pass only what caller gives (talk uses current + recent2)
# - Output: 3~4 lines, Korean 중심 + 일본어 조금 + emoji
# - Optional DB logging: public.ai_tutor_turns (RLS: auth.uid()=user_id)
# ============================================================

from __future__ import annotations

import os
import time
import hashlib
from typing import Any, Dict, Optional, Tuple

import streamlit as st

# Try to use core.get_authed_sb if available (Hotena shared core)
try:
    import core  # type: ignore
except Exception:  # pragma: no cover
    core = None  # type: ignore

# OpenAI SDK (new)
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


def _cfg(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v:
        return v
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


DEFAULT_MODEL = _cfg("OPENAI_MODEL_LOW", "gpt-4o-mini")
API_KEY = _cfg("OPENAI_API_KEY", "")
CACHE_TTL = int(_cfg("AI_CACHE_TTL_SEC", "180"))  # 3 min default
MAX_TURNS = int(_cfg("AI_MAX_CONTEXT_TURNS", "3"))  # kept for future
MAX_LINES = int(_cfg("AI_MAX_LINES", "4"))
MIN_LINES = int(_cfg("AI_MIN_LINES", "3"))


def _hash_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _get_cache(k: str) -> Optional[str]:
    try:
        c = st.session_state.get("_ai_cache_v1") or {}
        item = c.get(k)
        if not item:
            return None
        ts, val = item
        if (time.time() - float(ts)) > float(CACHE_TTL):
            return None
        return str(val)
    except Exception:
        return None


def _set_cache(k: str, val: str) -> None:
    try:
        c = st.session_state.get("_ai_cache_v1")
        if not isinstance(c, dict):
            c = {}
        c[k] = (time.time(), val)
        st.session_state["_ai_cache_v1"] = c
    except Exception:
        pass


def _normalize_lines(text: str, *, min_lines: int = MIN_LINES, max_lines: int = MAX_LINES) -> str:
    t = (text or "").strip()
    if not t:
        return "🙂 잠깐만요. 질문을 조금만 더 구체적으로 적어주실래요?\n例: どうしてこの表現？"
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if not lines:
        return "🙂 잠깐만요. 질문을 조금만 더 구체적으로 적어주실래요?\n例: どうしてこの表現？"
    # hard cap
    lines = lines[:max_lines]
    # pad if too short
    while len(lines) < min_lines:
        lines.append("（必要なら）例文をもう1つ作ってみましょう。")
    return "\n".join(lines)


def get_user_id() -> Optional[str]:
    u = st.session_state.get("user")
    return getattr(u, "id", None) if u else None


def _log_turn(
    *,
    mode: str,
    user_input: str,
    context: str,
    answer: str,
    model: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    # optional: requires core.get_authed_sb and table exists
    try:
        if core is None:
            return
        sb = core.get_authed_sb(force_refresh=False)  # type: ignore
        uid = get_user_id()
        if not sb or not uid:
            return
        payload = {
            "user_id": uid,
            "page": str((meta or {}).get("page") or ""),
            "mode": str(mode or ""),
            "qid": str((meta or {}).get("qid") or ""),
            "user_input": str(user_input or ""),
            "context": str(context or ""),
            "answer": str(answer or ""),
            "model": str(model or ""),
            "meta": meta or {},
        }
        sb.table("ai_tutor_turns").insert(payload).execute()
    except Exception:
        return


def ask_hatena(
    *,
    mode: str = "talk",
    user_input: str,
    context: str = "",
    meta: Optional[Dict[str, Any]] = None,
    min_lines: int = MIN_LINES,
    max_lines: int = MAX_LINES,
) -> str:
    """Main entrypoint for pages."""
    user_input = (user_input or "").strip()
    context = (context or "").strip()
    model = DEFAULT_MODEL

    # cache (same Q within ttl)
    ck = _hash_key(mode, user_input, context, model)
    cached = _get_cache(ck)
    if cached:
        return cached

    # fallback when OpenAI not set
    if not API_KEY or OpenAI is None:
        ans = _normalize_lines(
            "🙂 지금은 AI 설정이 꺼져 있어요.\n환경변수 OPENAI_API_KEY를 넣어주시면 하테나쌤이 바로 답해요.\n例: いまは準備中です。",
            min_lines=min_lines,
            max_lines=max_lines,
        )
        _set_cache(ck, ans)
        return ans

    client = OpenAI(api_key=API_KEY)

    sys = (
        "You are '하테나쌤', a friendly Japanese teacher (not a friend). "
        "Reply in 3-4 short lines. Korean 중심, 일본어는 조금 섞어. "
        "Be practical and specific. Use 1-2 emojis. "
        "Do NOT exceed 4 lines."
    )

    prompt = f"""[문맥]
{context}

[학생 질문]
{user_input}

[답변 규칙]
- 3~4줄, 짧고 실용적으로
- 한국어 중심 + 일본어 예시 1개 정도(있으면)
- 이모지 1~2개
"""

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=220,
        )
        raw = (res.choices[0].message.content or "").strip()
    except Exception:
        raw = "🙂 잠깐만요. 지금은 질문이 몰려서요.\n조금 있다가 다시 물어봐 주세요.\n例: 少し待ってね。"

    ans = _normalize_lines(raw, min_lines=min_lines, max_lines=max_lines)

    # DB log (best effort)
    try:
        _log_turn(mode=mode, user_input=user_input, context=context, answer=ans, model=model, meta=meta)
    except Exception:
        pass

    _set_cache(ck, ans)
    return ans
