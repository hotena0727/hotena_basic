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
import re
import time
from typing import Any, Dict, Optional, Tuple

import streamlit as st


def _safe_secrets_get(key: str, default: str = "") -> str:
    try:
        if hasattr(st, "secrets"):
            if hasattr(st.secrets, "get"):
                return st.secrets.get(key, default) or default
            return st.secrets[key] if key in st.secrets else default
    except Exception:
        return default
    return default

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

def _openai_chat(model: str, messages: list[dict[str, str]], *, max_output_tokens: int = 220) -> str:
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
        or _safe_secrets_get("OPENAI_API_KEY")
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
        "temperature": 0.4,
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


def _normalize_paragraphs(text: str, *, max_paras: int = 3) -> str:
    """Normalize talk-mode output while preserving paragraph breaks and limiting verbosity."""
    raw = (text or "").strip()
    if not raw:
        return quota_wait_message()

    # split by blank lines into paragraphs
    parts = re.split(r"\n\s*\n+", raw)
    paras = []
    for p in parts:
        p = " ".join([ln.strip() for ln in p.splitlines() if ln.strip()])
        if p:
            paras.append(p)

    if not paras:
        return quota_wait_message()

    # keep only first N paragraphs
    paras = paras[:max_paras]

    # sentence capping per paragraph (Japanese/English punctuation)
    def _split_sentences(s: str) -> list[str]:
        s = s.strip()
        if not s:
            return []
        # split after 。！？!?.
        chunks = re.split(r"(?<=[。！？!?\.])\s+", s)
        out = [c.strip() for c in chunks if c.strip()]
        return out if out else [s]

    caps = [1, 2, 2]  # p1,p2,p3
    capped = []
    for i, p in enumerate(paras):
        sents = _split_sentences(p)
        cap = caps[i] if i < len(caps) else 2
        p2 = " ".join(sents[:cap]).strip()
        capped.append(p2)

    # hard safety cap (characters) to prevent accidental long rambles
    joined = "\n\n".join(capped).strip()
    if len(joined) > 520:
        joined = joined[:520].rstrip()

    return joined



# ----------------------------
# Consult pitch (optional, periodic)
# ----------------------------
def _pitch_every_n() -> int:
    """How often to append consultation guidance in talk mode (default 7)."""
    try:
        v = int((_cfg("TALK_COACH_PITCH_EVERY") or "").strip() or "7")
        return max(3, min(v, 30))
    except Exception:
        return 7


def _talk_invocation_count_inc() -> int:
    key = "_talk_hatena_call_count"
    try:
        st.session_state[key] = int(st.session_state.get(key, 0)) + 1
    except Exception:
        st.session_state[key] = 1
    return int(st.session_state.get(key, 1))


def _score_bucket(score: Optional[float]) -> str:
    if score is None:
        return ""
    try:
        s = float(score)
    except Exception:
        return ""
    if s < 65:
        return "low"
    if s < 81:
        return "mid"
    return "high"


def _gen_consult_pitch(*, score: Optional[float], model: str) -> str:
    """Generate 1–2 line neutral consultation guidance (no salesy tone)."""
    bucket = _score_bucket(score)
    score_txt = f"{int(score)}" if isinstance(score, (int, float)) and score is not None else ""
    # Keep prompt compact (token saving)
    sys = "너는 일본어 회화 훈련 전문가다. 과장/판매/명령 표현 없이, 짧고 차분하게 한 줄~두 줄로 상담 안내 문구만 작성한다. '해결하세요' 같은 지시형 금지. '강의 등록/신청/결제' 단어 금지."
    if bucket == "low":
        user = f"최근 점수(대략 {score_txt}점)는 기본 구조 안정화가 필요한 단계로 보인다. '성장하고 싶다면 하테나쌤 상담을 통해 훈련 방향을 안내받을 수 있다'는 취지로 1~2줄."
    elif bucket == "mid":
        user = f"최근 점수(대략 {score_txt}점)는 구조는 이해했으나 자동화가 부족한 단계로 보인다. 상담 안내 1~2줄."
    elif bucket == "high":
        user = f"최근 점수(대략 {score_txt}점)는 안정적이다. 다음 단계(자연스러움/표현 밀도) 점검을 상담으로 안내받을 수 있다는 1~2줄."
    else:
        user = "최근 학습 흐름을 바탕으로 다음 훈련 방향이 고민될 때 하테나쌤 상담으로 안내받을 수 있다는 1~2줄."
    txt = _openai_chat(model, [{"role":"system","content":sys},{"role":"user","content":user}], max_output_tokens=90)
    # normalize: 1~2 lines
    lines = [ln.strip() for ln in (txt or "").splitlines() if ln.strip()]
    if not lines:
        return ""
    lines = lines[:2]
    return "\n".join(lines).strip()


def _maybe_append_consult_pitch(ans: str, *, mode: str, user_input: str, context: str, meta: dict | None, model: str) -> str:
    """Append periodic consultation guidance to talk-mode answer."""
    if (mode or "").lower().strip() != "talk":
        return ans
    # Count every invocation (including cache hits), but do not cache the appended pitch.
    cnt = _talk_invocation_count_inc()
    every = _pitch_every_n()
    if cnt % every != 0:
        return ans

    qid = None
    if isinstance(meta, dict):
        qid = meta.get("qid")
    score = None
    if qid:
        try:
            score = st.session_state.get(f"{qid}_pron_score")
            if score is None:
                score = st.session_state.get(f"{qid}_pron_score_last")
        except Exception:
            score = None

    pitch = _gen_consult_pitch(score=score, model=model)
    if not pitch:
        return ans

    # Append as last paragraph
    return (ans or "").rstrip() + "\n\n" + pitch

def _system_prompt(mode: str) -> str:
    # Keep consistent tone: teacher but kind, KR-first, small JP mix
    base = [
        "너는 일본어 학습 앱 '하테나'의 AI 튜터 '하테나쌤'이다.",
        "친절한 선생님 톤으로, 핵심만 짚어서 짧게 답한다.",
        "답변은 기본 한국어 중심으로 하되, 일본어 설명을 1줄 정도 섞는다.",
        "(explain 모드) 전체 답변은 3~4줄로 제한한다. (줄바꿈으로 3~4줄) — talk 모드에는 적용하지 않는다.",
        "이모지는 필수가 아니다. 필요하면 1개 이하로만 사용한다.",
        "긴 강의처럼 말하지 말고, 학습자가 바로 이해/말하기를 이어가게 한다.",
        "추가 질문을 하지 않는다. 사용자의 다음 행동을 요구하지 않는다.",
        "반드시 피드백 문장으로 끝낸다. 격려/응원 문구는 넣지 않는다.",
    ]
    m = (mode or "").lower().strip()
    if m == "talk":
        base += [
            "모드: 회화 코칭. 정답/오답을 단정적으로 몰아붙이지 말고, 학생이 바로 말로 이어가게 돕는다.",
            "답변은 번호(1.,2.,3.)나 [해결] 같은 라벨 없이 자연스럽게 작성한다.",
            "답변은 번호/라벨 없이 2문단으로 쓴다. 문단 사이에는 빈 줄 1줄을 둔다.",
            "1문단: 질문에 대한 직접 해결(1~2문장).",
            "2문단: 추가 정보/뉘앙스 + 더 자연스러운 대안 1개(1~2문장).",
            "문단별 문장 수를 제한한다: 1문단 1문장, 2문단 최대 2문장. 장황한 서론/캐릭터 설정은 1문장 이상 쓰지 않는다.",
            "말투는 따뜻하고 부드럽게, 과하게 딱딱한 표현은 피한다.",
            "중요: 사용자의 질문이 제공된 상황/문맥과 무관해 보이면, 문맥을 억지로 끼워 맞추지 말고 질문을 우선으로 답한다. 필요하면 문맥은 간단히 무시한다.",
            "추가 질문은 하지 않는다. (다만 상황에 따라 선택지 형태로 짧게 덧붙이는 건 허용)",
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

    m = (mode or "").lower().strip()
    if m == "talk":
        hint = "(2문단: 해결(1문장) / 추가정보+대안(최대2문장). 문단 사이 빈 줄 1줄)"
    else:
        hint = "(3~4줄로 짧게)"

    if cx:
        user = f"질문: {u}\n상황/문맥: {cx}\n{hint}"
    else:
        user = f"질문: {u}\n{hint}"

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
        # Even on cache hit, we may append periodic consultation guidance (talk mode only).
        model = _cfg("OPENAI_MODEL_LOW") or DEFAULT_MODEL_LOW
        return _maybe_append_consult_pitch(cached, mode=mode, user_input=user_input, context=context, meta=_meta, model=model)

    # Must be logged in (DB quota uses auth.uid())
    if not get_user_id():
        return need_login_message()

    # Admin bypass (unlimited)
    admin_override = bool(_meta.get("is_admin")) or _is_admin_debug()
    if not admin_override:
        # Quota check (consumes 1 when allowed)
        allowed, _, _ = check_and_consume_quota()
        if not allowed:
            return quota_wait_message()

    # Model selection (low-cost)
    model = _cfg("OPENAI_MODEL_LOW") or DEFAULT_MODEL_LOW

    # Build messages and call
    messages = _build_messages(mode, user_input, context)
    max_toks = 240 if (mode or "").lower().strip() == "talk" else 220
    raw = _openai_chat(model, messages, max_output_tokens=max_toks)

    # Normalize (cache base answer only; pitch is appended per-call)
    if (mode or "").lower().strip() == "talk":
        if min_lines == MIN_LINES_DEFAULT:
            min_lines = 3
        if max_lines == MAX_LINES_DEFAULT:
            max_lines = 6
    if (mode or "").lower().strip() == "talk":
        base_ans = _normalize_paragraphs(raw, max_paras=3)
    else:
        base_ans = _normalize_lines(raw, min_lines=min_lines, max_lines=max_lines)

    # Cache the base answer (no pitch)
    set_cached_answer(mode, user_input, context, base_ans)

    # Optionally append consultation guidance periodically (talk mode only)
    ans = _maybe_append_consult_pitch(base_ans, mode=mode, user_input=user_input, context=context, meta=_meta, model=model)
    return ans
