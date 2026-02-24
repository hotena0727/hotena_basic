# ai_tutor.py
# ============================================================
# ✅ Hatena Teacher (하테나쌤) — Request-only AI helper for talk/explain
#
# Goals
# - Cheap model by default (OPENAI_MODEL_LOW, fallback: gpt-4o-mini)
# - Korean-first explanations + small Japanese mix
# - Short answers: 3–4 lines, 1 emoji at most (soft rule)
# - Daily quota (DB/Supabase): free=1, pro=5  (plan == "pro")
# - Cache identical questions for a few minutes (cache hits do NOT consume quota)
#
# Dependencies
# - Uses your existing core.py for auth + Supabase authed client
# - Calls Supabase RPC: public.ai_check_and_inc_kst(max_uses int)
# - Calls OpenAI Chat Completions API via HTTPS (requests)
# ============================================================

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

import streamlit as st

# Local imports from your project
import core

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


# ----------------------------
# Config
# ----------------------------
DEFAULT_MODEL_LOW = "gpt-4o-mini"
CACHE_TTL_SECONDS = 180  # 3 minutes (tweak: 60~300)
MAX_LINES_DEFAULT = 4
MIN_LINES_DEFAULT = 3


def _cfg(key: str) -> str:
    return core.get_cfg(key)


def _now() -> float:
    return time.time()


# ----------------------------
# User / Plan
# ----------------------------
def get_user_id() -> Optional[str]:
    """Return Supabase user id from session_state (robust to dict/object)."""
    u = st.session_state.get("user")
    if not u:
        return None
    # supabase-py user object usually has .id
    uid = getattr(u, "id", None)
    if uid:
        return str(uid)
    # sometimes dict-like
    if isinstance(u, dict) and u.get("id"):
        return str(u["id"])
    return None


def get_user_plan(*, force_refresh: bool = False) -> str:
    """
    Read plan from profiles.plan via core.load_profile.
    Cached in st.session_state["user_plan"] for performance.
    """
    # cache with timestamp
    cache_key = "_ai_user_plan_cached_at"
    if not force_refresh and st.session_state.get("user_plan") and st.session_state.get(cache_key):
        # 10 minutes cache
        if _now() - float(st.session_state.get(cache_key, 0.0)) < 600:
            return str(st.session_state.get("user_plan") or "")

    sb = core.get_authed_sb(force_refresh=True)
    uid = get_user_id()
    if not sb or not uid:
        st.session_state["user_plan"] = ""
        st.session_state[cache_key] = _now()
        return ""

    prof = core.load_profile(sb, uid) or {}
    plan = str(prof.get("plan") or "")
    st.session_state["user_plan"] = plan
    st.session_state[cache_key] = _now()
    return plan


def _max_uses_for_plan(plan: str) -> int:
    return 5 if (plan or "").lower() == "pro" else 1


# ----------------------------
# Quota (DB via Supabase RPC)
# ----------------------------
def check_and_consume_quota() -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Returns (allowed, used, remaining).
    - Requires authenticated user (Supabase auth.uid()).
    - Consumes 1 quota when allowed=True.
    """
    sb = core.get_authed_sb(force_refresh=True)
    uid = get_user_id()
    if not sb or not uid:
        return False, None, None

    plan = get_user_plan(force_refresh=False)
    max_uses = _max_uses_for_plan(plan)

    try:
        res = sb.rpc("ai_check_and_inc_kst", {"max_uses": max_uses}).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            row = data[0] or {}
            allowed = bool(row.get("allowed"))
            used = int(row.get("used")) if row.get("used") is not None else None
            remaining = int(row.get("remaining")) if row.get("remaining") is not None else None
            return allowed, used, remaining
    except Exception:
        pass

    return False, None, None


def quota_wait_message() -> str:
    # Keep it short, friendly, and not revealing numbers.
    return "\n".join(
        [
            "💬 지금은 질문이 잠깐 몰려 있어요.",
            "조금 있다가 다시 물어봐 주세요 🙂",
            "질문을 한 문장으로 짧게 적으면 더 빨리 도와드릴게요.",
        ]
    )


def need_login_message() -> str:
    return "\n".join(
        [
            "💬 하테나쌤은 로그인 후 사용할 수 있어요.",
            "먼저 로그인하고 다시 물어봐 주세요 🙂",
            "필요하면 ‘MY’에서 로그인 상태를 확인해 주세요.",
        ]
    )


# ----------------------------
# Cache (no quota on hit)
# ----------------------------
def _cache_bucket() -> Dict[str, Any]:
    if "ai_cache" not in st.session_state or not isinstance(st.session_state.get("ai_cache"), dict):
        st.session_state["ai_cache"] = {}
    return st.session_state["ai_cache"]


def _cache_key(mode: str, user_input: str, context: str) -> str:
    # Keep it simple; include mode + normalized input + small context
    m = (mode or "").strip().lower()
    ui = " ".join((user_input or "").strip().split())
    cx = " ".join((context or "").strip().split())
    return f"{m}||{ui}||{cx}"[:800]


def get_cached_answer(mode: str, user_input: str, context: str) -> Optional[str]:
    bucket = _cache_bucket()
    k = _cache_key(mode, user_input, context)
    item = bucket.get(k)
    if not item or not isinstance(item, dict):
        return None
    ts = float(item.get("ts", 0.0))
    if _now() - ts > CACHE_TTL_SECONDS:
        bucket.pop(k, None)
        return None
    ans = item.get("answer")
    return str(ans) if isinstance(ans, str) and ans else None


def set_cached_answer(mode: str, user_input: str, context: str, answer: str) -> None:
    bucket = _cache_bucket()
    k = _cache_key(mode, user_input, context)
    bucket[k] = {"ts": _now(), "answer": answer}


# ----------------------------
# OpenAI call (Chat Completions)
# ----------------------------
def _openai_chat(model: str, messages: list[dict[str, str]], *, max_output_tokens: int = 220) -> str:
    """
    Calls OpenAI Chat Completions API.
    Requires OPENAI_API_KEY in env or st.secrets.
    """
    if requests is None:
        return "💬 서버 설정 문제로 잠시 답변이 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂\n(관리자: requests 설치 확인)"
    api_key = _cfg("OPENAI_API_KEY")
    if not api_key:
        return "💬 하테나쌤 설정이 아직 준비되지 않았어요.\n조금 있다가 다시 물어봐 주세요 🙂\n(관리자: OPENAI_API_KEY 설정)"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": max_output_tokens,
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=18)
        if r.status_code >= 400:
            return "💬 지금은 답변이 조금 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂\n(잠시 후 재시도)"
        data = r.json()
        choices = data.get("choices") or []
        if choices and choices[0].get("message") and choices[0]["message"].get("content"):
            return str(choices[0]["message"]["content"]).strip()
    except Exception:
        pass
    return "💬 지금은 답변이 조금 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂\n(잠시 후 재시도)"


# ----------------------------
# Formatting helpers
# ----------------------------
def _normalize_lines(text: str, *, min_lines: int = MIN_LINES_DEFAULT, max_lines: int = MAX_LINES_DEFAULT) -> str:
    # split, trim blanks
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return quota_wait_message()
    # hard cap
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    # if too short, keep as-is (we don't want to force verbosity)
    # but we can attempt to merge if it's too many short fragments
    if len(lines) < min_lines:
        # allow 1-2 lines if model answered short; still okay
        return "\n".join(lines)
    return "\n".join(lines)


def _system_prompt(mode: str) -> str:
    # Keep consistent tone: teacher but kind, KR-first, small JP mix
    base = [
        "너는 일본어 학습 앱 '하테나'의 AI 튜터 '하테나쌤'이다.",
        "친절한 선생님 톤으로, 핵심만 짚어서 짧게 답한다.",
        "답변은 기본 한국어 중심으로 하되, 일본어 설명을 1줄 정도 섞는다.",
        "전체 답변은 3~4줄로 제한한다. (줄바꿈으로 3~4줄)",
        "이모지는 최대 1개만 사용한다. (가능하면 📘 또는 💬)",
        "긴 강의처럼 말하지 말고, 학습자가 바로 이해/말하기를 이어가게 한다.",
    ]
    m = (mode or "").lower().strip()
    if m == "talk":
        base += [
            "모드: 회화 자신감. 문장을 크게 '틀렸어요'라고 단정하지 않는다.",
            "필요하면 아주 가볍게 더 자연스러운 표현을 1개 제시하고, 마지막 줄은 다음 질문 1개로 끝낸다.",
        ]
    else:
        base += [
            "모드: 이해력 보조. 한 줄 요점 → 한 줄 일본어 설명 → 예문(최대 1개) 순서를 선호한다.",
        ]
    return " ".join(base)


def _build_messages(mode: str, user_input: str, context: str) -> list[dict[str, str]]:
    sys = _system_prompt(mode)
    # Keep user message compact to save tokens
    u = user_input.strip()
    cx = (context or "").strip()
    if cx:
        user = f"질문: {u}\n상황/문맥: {cx}\n(3~4줄로 짧게)"
    else:
        user = f"질문: {u}\n(3~4줄로 짧게)"
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]



# ----------------------------
# DB logging (optional, cheap)
# - Stores AI Q/A for audit/support
# - Create table: public.ai_tutor_turns (see SQL below)
# ----------------------------
def _log_interaction(
    *,
    mode: str,
    user_input: str,
    context: str,
    answer: str,
    model: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        sb = core.get_authed_sb(force_refresh=False)
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
        # table insert (RLS: auth.uid() == user_id)
        sb.table("ai_tutor_turns").insert(payload).execute()
    except Exception:
        # never break UX
        return


# ----------------------------
# Public API
# ----------------------------
def ask_hatena(
    *,
    mode: str = "explain",
    user_input: str,
    context: str = "",
    meta: Optional[Dict[str, Any]] = None,
    min_lines: int = MIN_LINES_DEFAULT,
    max_lines: int = MAX_LINES_DEFAULT,
) -> str:
    """
    Main entry:
    - Cache hit -> return cached answer (no quota consumption)
    - If not logged in -> friendly login message
    - Check quota via DB RPC (consumes 1) before OpenAI call
    - Return short 3–4 line answer
    """
    # Ensure core exists & session is refreshed
    core.ensure_core()
    core.refresh_session_from_cookie_if_needed(force=False)

    # Cache check first (free)
    cached = get_cached_answer(mode, user_input, context)
    if cached:
        return cached

    # Must be logged in (DB quota uses auth.uid())
    if not get_user_id():
        return need_login_message()

    # Quota check (consumes 1 when allowed)
    allowed, _, _ = check_and_consume_quota()
    if not allowed:
        return quota_wait_message()

    # Model selection (low-cost)
    model = _cfg("OPENAI_MODEL_LOW") or DEFAULT_MODEL_LOW

    # Build messages and call
    messages = _build_messages(mode, user_input, context)
    raw = _openai_chat(model, messages, max_output_tokens=220)

    # Normalize + cache
    ans = _normalize_lines(raw, min_lines=min_lines, max_lines=max_lines)
    set_cached_answer(mode, user_input, context, ans)
    return ans
