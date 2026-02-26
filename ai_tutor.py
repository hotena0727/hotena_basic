# ai_tutor.py
# ============================================================
# ✅ Hatena Teacher (하테나쌤) — Request-only AI helper for talk/explain
#
# 핵심 목표
# - 기본 모델: gpt-4o-mini (환경변수 OPENAI_MODEL_LOW로 변경 가능)
# - 한국어 중심 + 일본어 1줄 정도
# - 짧게 3~4줄
# - (중요) 추가 질문/질문 유도 금지: "다음 질문은?" 같은 문장 금지
# - 일일 쿼터: free=1, pro=5 (DB RPC: public.ai_check_and_inc_kst)
# - (요청 반영) 관리자(admin)는 무제한: 쿼터 RPC를 타지 않음
# ============================================================

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

import streamlit as st
import core

# ----------------------------
# Config
# ----------------------------
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
CACHE_TTL_SECONDS = 180  # 3 minutes
MIN_LINES_DEFAULT = 3
MAX_LINES_DEFAULT = 4


def _now() -> float:
    return time.time()


def _is_admin_debug() -> bool:
    # UI/로그에 디버그를 노출할지 여부(관리자만)
    return bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False))


def get_user_id() -> Optional[str]:
    u = st.session_state.get("user")
    uid = getattr(u, "id", None) if u else None
    if uid:
        return str(uid)
    # fallback: token 기반(환경에 따라 core가 처리)
    return str(st.session_state.get("user_id") or "") or None


def get_user_plan(*, force_refresh: bool = False) -> str:
    """Return plan string ('free'|'pro'|...). Cached in session_state['user_plan']."""
    cache_key = "_ai_user_plan_cached_at"
    if not force_refresh and st.session_state.get("user_plan") and st.session_state.get(cache_key):
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
    - Fast path: st.session_state['is_admin'] or ['is_admin_cached']
    - Slow path: profiles.is_admin via core.load_profile (cached 10 min)
    """
    if bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False)):
        return True

    cache_key = "_ai_is_admin_cached_at"
    val_key = "_ai_is_admin_cached_val"
    if not force_refresh and cache_key in st.session_state:
        if _now() - float(st.session_state.get(cache_key, 0.0)) < 600:
            return bool(st.session_state.get(val_key, False))

    sb = core.get_authed_sb(force_refresh=True)
    uid = get_user_id()
    if not sb or not uid:
        st.session_state[cache_key] = _now()
        st.session_state[val_key] = False
        return False

    prof = core.load_profile(sb, uid) or {}
    is_admin = bool(prof.get("is_admin", False))
    st.session_state[cache_key] = _now()
    st.session_state[val_key] = is_admin
    # 홈/허브에서 쓰는 캐시 키가 있다면 같이 갱신(호환)
    st.session_state["is_admin_cached"] = is_admin
    return is_admin


def _max_uses_for_plan(plan: str) -> int:
    return 5 if (plan or "").lower() == "pro" else 1


# ----------------------------
# Quota (DB via Supabase RPC)
# ----------------------------
def check_and_consume_quota() -> Tuple[bool, Optional[int], Optional[int], str]:
    """
    Returns (allowed, used, remaining, last_error).
    - Admin: unlimited (skip RPC)
    - Others: consumes 1 quota when allowed=True via RPC
    """
    # ✅ Admin unlimited
    if get_is_admin(force_refresh=False):
        return True, None, None, ""

    sb = core.get_authed_sb(force_refresh=True)
    uid = get_user_id()
    if not sb or not uid:
        return False, None, None, "NO_SB_OR_UID"

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
            return allowed, used, remaining, ""
        return False, None, None, "EMPTY_RPC_DATA"
    except Exception as e:
        return False, None, None, f"RPC_EXCEPTION: {e}"



def quota_wait_message() -> str:
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
    m = (mode or "").strip().lower()
    u = (user_input or "").strip()
    cx = (context or "").strip()
    # 캐시 충돌 줄이기: 짧게 해시(필요시)
    return f"{m}::{u}::{cx}"


def _cache_get(mode: str, user_input: str, context: str) -> Optional[str]:
    bucket = _cache_bucket()
    k = _cache_key(mode, user_input, context)
    it = bucket.get(k)
    if not it:
        return None
    try:
        ts = float(it.get("ts", 0.0))
        if _now() - ts > CACHE_TTL_SECONDS:
            bucket.pop(k, None)
            return None
        return str(it.get("v") or "")
    except Exception:
        return None


def _cache_set(mode: str, user_input: str, context: str, value: str) -> None:
    bucket = _cache_bucket()
    k = _cache_key(mode, user_input, context)
    bucket[k] = {"ts": _now(), "v": value}


# ----------------------------
# Prompt
# ----------------------------
def _system_prompt(mode: str) -> str:
    # 질문 유도 금지, 물음표로 끝내지 않기
    base = [
        "너는 일본어 학습 앱 '하테나'의 AI 튜터 '하테나쌤'이다.",
        "친절한 코치 톤으로 핵심만 짚어 짧게 답한다.",
        "답변은 한국어 중심으로 하되, 일본어 설명을 1줄 정도 섞는다.",
        "전체 답변은 줄바꿈 기준 3~4줄로 제한한다.",
        "이모지는 최대 1개만 사용한다.",
        "절대 추가 질문을 하지 않는다. 대화를 이어가려 하지 않는다.",
        "사용자에게 다음 행동/질문을 요구하지 않는다.",
        "답변 마지막에 물음표(?)를 쓰지 않는다. '다음 질문은?' 같은 문장을 금지한다.",
        "반드시 피드백 문장으로 끝낸다.",
    ]
    m = (mode or "").lower().strip()
    if m == "talk":
        base += [
            "모드: 회화 코칭. 틀림을 단정하기보다 자연스럽게 교정한다.",
            "필요하면 더 자연스러운 표현을 1개만 제시한다.",
        ]
    else:
        base += [
            "모드: 이해력 보조. 요점 1줄 → 일본어 1줄 → 예문(최대 1개) 순서를 선호한다.",
        ]
    return " ".join(base)


def _build_messages(mode: str, user_input: str, context: str) -> list[dict[str, str]]:
    sys = _system_prompt(mode)
    u = (user_input or "").strip()
    cx = (context or "").strip()
    if cx:
        user = f"질문/상황: {u}\n문맥: {cx}\n(3~4줄로)"
    else:
        user = f"질문/상황: {u}\n(3~4줄로)"
    return [{"role": "system", "content": sys}, {"role": "user", "content": user}]


# ----------------------------
# OpenAI call
# ----------------------------
def _openai_chat(*, model: str, messages: list[dict[str, str]], temperature: float = 0.55, max_tokens: int = 220) -> str:
    # Import lazily
    try:
        import requests
    except Exception as e:
        if _is_admin_debug():
            return f"(AI) requests import error: {e}"
        return "💬 서버 설정 문제로 잠시 답변이 어려워요.\n조금 있다가 다시 물어봐 주세요 🙂"

    api_key = (st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None) or st.session_state.get("OPENAI_API_KEY")
    if not api_key:
        if _is_admin_debug():
            return "(AI) missing OPENAI_API_KEY"
        return "💬 하테나쌤 설정이 아직 준비되지 않았어요.\n조금 있다가 다시 물어봐 주세요 🙂"

    payload = {"model": model, "messages": messages, "temperature": float(temperature), "max_tokens": int(max_tokens)}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        r = requests.post(OPENAI_URL, headers=headers, data=json.dumps(payload), timeout=30)
        if r.status_code >= 400:
            if _is_admin_debug():
                return f"(AI HTTP {r.status_code}) {r.text[:400]}"
            return "💬 잠시 답변이 어려워요.\n조금 있다가 다시 시도해 주세요 🙂"
        data = r.json()
        return (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "") or ""
    except Exception as e:
        if _is_admin_debug():
            return f"(AI EXC) {e}"
        return "💬 잠시 답변이 어려워요.\n조금 있다가 다시 시도해 주세요 🙂"


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
    """
    Main entry:
    - Cache hit -> return cached answer (no quota consumption)
    - If not logged in -> friendly login message
    - Check quota via DB RPC (consumes 1) before OpenAI call (admin unlimited)
    - Return short 3–4 line answer
    """
    _ = meta or {}

    # Cache first
    cached = _cache_get(mode, user_input, context)
    if cached:
        return cached

    # Ensure session/auth ready
    core.ensure_session_user()

    uid = get_user_id()
    if not uid:
        return need_login_message()

    allowed, used, remaining, last_error = check_and_consume_quota()
    if not allowed:
        if _is_admin_debug():
            return f"(Quota denied) uid={uid} plan={get_user_plan()} used={used} remaining={remaining} last_error={last_error}"
        return quota_wait_message()

    model = str(st.session_state.get("OPENAI_MODEL_LOW") or st.secrets.get("OPENAI_MODEL_LOW") if hasattr(st, "secrets") else "") or DEFAULT_MODEL
    messages = _build_messages(mode, user_input, context)
    ans = _openai_chat(model=model, messages=messages, temperature=0.6, max_tokens=240).strip()

    # Hard trim to 3~4 lines
    lines = [ln.strip() for ln in ans.splitlines() if ln.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) < min_lines and lines:
        # pad softly without 질문 유도
        while len(lines) < min_lines:
            lines.append("한 줄만 더 자연스럽게 다듬어도 좋아요.")
    ans2 = "\n".join(lines) if lines else quota_wait_message()

    _cache_set(mode, user_input, context, ans2)
    return ans2
