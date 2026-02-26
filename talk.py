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
# Debug (admin only)
# ----------------------------
def _is_admin_debug() -> bool:
    return bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False))

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



def get_is_admin(*, force_refresh: bool = False) -> bool:
    """Return whether current user is admin.
    - Fast path: st.session_state flags
    - Slow path: profiles.is_admin via core.load_profile (cached 10 min)
    """
    if bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False)):
        return True

    cache_key = "_ai_is_admin_cached_at"
    val_key = "_ai_is_admin_cached_val"
    if not force_refresh and cache_key in st.session_state:
        try:
            if _now() - float(st.session_state.get(cache_key, 0.0)) < 600:
                return bool(st.session_state.get(val_key, False))
        except Exception:
            pass

    sb = core.get_authed_sb(force_refresh=True)
    uid = get_user_id()
    if not sb or not uid:
        st.session_state[val_key] = False
        st.session_state[cache_key] = _now()
        return False

    prof = core.load_profile(sb, uid) or {}
    is_admin = bool(prof.get("is_admin", False))
    st.session_state[val_key] = is_admin
    st.session_state[cache_key] = _now()
    return is_admin

def _max_uses_for_plan(plan: str) -> int:
    return 5 if (plan or "").lower() == "pro" else 1


# ----------------------------
# Quota (DB via Supabase RPC)
# ----------------------------
def check_and_consume_quota() -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Returns (allowed, used, remaining).
    - Requires authenticated user (Supabase auth.uid()) for normal users.
    - 관리자(get_is_admin()==True)는 하루 사용량 무제한: DB quota를 소비하지 않고 항상 allowed=True.
    """
    # ✅ Admin: unlimited, no DB writes
    if get_is_admin(force_refresh=False):
        return True, None, None

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
            used_val = int(row.get("used")) if row.get("used") is not None else None
            remaining_val = int(row.get("remaining")) if row.get("remaining") is not None else None
            return allowed, used_val, remaining_val
    except Exception:
        pass

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
            "🙂 잠깐만요. 지금은 질문이 몰려서요.",
            "조금 있다가 다시 물어봐 주세요.",
            "例: 少し待ってね。",
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

def _openai_chat(model: str, messages: list[dict[str, str]], *, max_output_tokens: int = 220, temperature: float = 0.55) -> str:
    """
    Calls OpenAI Chat Completions API.
    - 관리자(is_admin)에게만 실패 원인(HTTP/예외)을 노출
    - API KEY 읽기 경로를 통합(core cfg -> st.secrets -> env)
    """
    if requests is None:
        msg = "(관리자: requests 설치 확인)"
        return msg if _is_admin_debug() else "💬 서버 설정 문제로 잠시 답변이 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂\n(관리자: requests 설치 확인)"

    import os

    api_key = (
        _cfg("OPENAI_API_KEY")
        or st.secrets.get("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )

    if not api_key:
        msg = "(관리자: OPENAI_API_KEY 설정 없음: core.get_cfg / st.secrets / env 모두 비어있음)"
        return msg if _is_admin_debug() else "💬 하테나쌤 설정이 아직 준비되지 않았어요.\n조금 있다가 다시 물어봐 주세요 🙂\n(관리자: OPENAI_API_KEY 설정)"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": max_output_tokens,
    }

    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=18)

        if r.status_code >= 400:
            # ✅ 관리자에게만 원문 일부 노출
            if _is_admin_debug():
                body = (r.text or "")[:1200]
                return f"(OpenAI HTTP {r.status_code}) {body}"
            return "💬 지금은 답변이 조금 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂\n(잠시 후 재시도)"

        data = r.json()
        choices = data.get("choices") or []
        if choices and choices[0].get("message") and choices[0]["message"].get("content"):
            return str(choices[0]["message"]["content"]).strip()

        # JSON 구조가 예상과 다를 때(관리자만)
        if _is_admin_debug():
            return f"(OpenAI 응답 파싱 실패) {str(data)[:800]}"

    except Exception as e:
        if _is_admin_debug():
            return f"(OpenAI 예외) {repr(e)}"
        return "💬 지금은 답변이 조금 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂\n(잠시 후 재시도)"

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
    """System prompt for Hatena-sensei.
    목표: '코치'답게 짧고 다양하게, 그리고 절대 질문으로 끝내지 않기.
    """
    base = [
        "너는 일본어 학습 앱 '하테나'의 AI 튜터 '하테나쌤'이다.",
        "역할은 대화 상대가 아니라 '스마트 코치'다. 사용자를 시험하지 않는다.",
        "답변은 한국어 중심 + 일본어(1줄 이내)만 섞는다.",
        "전체는 2~4줄로 짧게. 장문 금지.",
        "이모지는 최대 1개.",
        "추가 질문/후속 질문/대화 유도 문장 금지. 물음표(?)로 끝내지 말 것.",
        "반드시 피드백으로 종료한다. 사용자의 다음 행동을 요구하지 않는다.",
        "가능하면 아래 형식을 따른다: (1)평가 1줄 (2)더 자연스러운 표현 1줄 (3)한줄 이유/팁 1줄.",
    ]
    m = (mode or "").lower().strip()
    if m == "talk":
        base += [
            "모드: 회화 자신감 코칭.",
            "정답/오답을 딱 잘라 단정하지 말고, 자연스러움/뉘앙스 중심으로 교정한다.",
            "대안 표현은 1개만. 너무 많은 옵션 금지.",
        ]
    else:
        base += [
            "모드: 이해력 보조.",
            "요점 1줄 → 일본어 1줄 → (필요할 때만) 짧은 예문 1개 순서.",
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
# Public API
# ----------------------------
def ask_hatena(
    *,
    mode: str = "explain",
    user_input: str,
    context: str = "",
    meta: dict | None = None,
    min_lines: int = MIN_LINES_DEFAULT,
    max_lines: int = MAX_LINES_DEFAULT,
) -> str:
    _meta = meta or {}
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
    raw = _openai_chat(model, messages, max_output_tokens=220, temperature=(0.75 if mode.lower().strip()=="talk" else 0.55))

    # Normalize + cache
    ans = _normalize_lines(raw, min_lines=min_lines, max_lines=max_lines)
    set_cached_answer(mode, user_input, context, ans)
    return ans
