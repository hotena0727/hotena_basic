from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st


# ============================================================
# ✅ MyPage (Refactor v10 - AdminStyle Clean (Hub/Home + No Top Msg))
# - "개발자 느낌" 제거: 표/기본차트/엑셀형 UI 지양
# - 위계: 숫자(KPI) → 흐름(상태) → 행동(CTA) → 상세(카드)
# - 색: 하테나 블루(강조/액션) + 중립 톤
# - 기능: wrong_notes(오답 상세) / quiz_attempts(학습 기록) / user_messages(메시지)
# ============================================================


# ---------- Supabase helpers ----------
def _sb() -> Any:
    """Return Supabase client with JWT bound for RLS (if available)."""
    sb = st.session_state.get("sb_authed") or st.session_state.get("sb")
    token = st.session_state.get("access_token")
    if sb and token:
        try:
            sb.postgrest.auth(token)
        except Exception:
            pass
    return sb


def _user() -> Any:
    return st.session_state.get("user")


def _user_id(user: Any) -> Optional[str]:
    if not user:
        return None
    if isinstance(user, dict):
        return user.get("id") or (user.get("user") or {}).get("id")
    if hasattr(user, "id"):
        return getattr(user, "id")
    if hasattr(user, "user") and getattr(user, "user") is not None:
        u = getattr(user, "user")
        if isinstance(u, dict):
            return u.get("id")
        if hasattr(u, "id"):
            return getattr(u, "id", None)
    return None


def _user_email(user: Any) -> Optional[str]:
    if not user:
        return None
    if isinstance(user, dict):
        return user.get("email") or (user.get("user") or {}).get("email")
    if hasattr(user, "email") and getattr(user, "email"):
        return getattr(user, "email")
    if hasattr(user, "user") and getattr(user, "user") is not None:
        u = getattr(user, "user")
        if isinstance(u, dict):
            return u.get("email")
        if hasattr(u, "email"):
            return getattr(u, "email", None)
    return None


def _safe_select(table: str, cols: str = "*", order_col: str = "created_at", limit: int = 200) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        r = sb.table(table).select(cols).order(order_col, desc=True).limit(limit).execute()
        return getattr(r, "data", None) or []
    except Exception:
        return []


def _safe_update(table: str, values: Dict[str, Any], where_col: str, where_val: Any):
    sb = _sb()
    if not sb:
        return
    try:
        sb.table(table).update(values).eq(where_col, where_val).execute()
    except Exception:
        pass


# ---------- formatting / parsing ----------
def _fmt_dt(v: Any) -> str:
    if not v:
        return ""
    s = str(v).replace("T", " ")
    return s[:16]


def _parse_dt(v: Any) -> Optional[datetime]:
    if not v:
        return None
    try:
        s = str(v)
        # Supabase ISO: 2026-02-21T14:29:00+00:00
        # datetime.fromisoformat handles offset.
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------- UI CSS ----------
def _css():
    st.markdown(
        """
<style>
:root{
  --ha-blue:#2F6BFF;
  --ha-text:#0f172a;
  --ha-muted:rgba(15,23,42,.60);
  --ha-line:rgba(0,0,0,.08);
  --ha-soft:rgba(0,0,0,.04);
}


.ha-wrap{max-width:none;width:100%;margin:0;box-sizing:border-box;}
.ha-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:10px 0 14px;}
.ha-card{background:linear-gradient(180deg, rgba(0,0,0,.035), rgba(0,0,0,.015));
  border:1px solid rgba(0,0,0,.08);border-radius:18px;padding:14px 14px 12px;}
.ha-k{font-size:12px;opacity:.65;margin-bottom:6px;}
.ha-v{font-size:24px;font-weight:800;letter-spacing:-0.02em;line-height:1.1;}
.ha-s{font-size:12px;opacity:.55;margin-top:6px;}
.ha-section{border:1px solid rgba(0,0,0,.08);border-radius:18px;padding:14px;margin:10px 0;background:rgba(255,255,255,.65);}
.ha-title{font-size:15px;font-weight:800;margin:0 0 8px 0;}
.ha-sub{font-size:12px;opacity:.65;margin:0 0 10px 0;}
.ha-pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;
  background:rgba(0,0,0,.04);border:1px solid rgba(0,0,0,.08);font-size:12px;opacity:.85;}
@media (max-width:900px){.ha-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}

.ha-log{display:flex;flex-direction:column;gap:10px;margin-top:10px;}
.ha-logcard{background:rgba(255,255,255,.82);border:1px solid rgba(0,0,0,.08);border-radius:18px;padding:14px;}
.ha-logtop{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;}
.ha-email{font-weight:800;letter-spacing:-0.02em;}
.ha-time{font-size:12px;opacity:.65;margin-top:2px;display:flex;align-items:center;gap:6px;}
.ha-badges{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end;}
.ha-badge{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;
  background:rgba(0,0,0,.04);border:1px solid rgba(0,0,0,.08);font-size:12px;opacity:.9;}
.ha-badge.ok{background:rgba(0,128,0,.06);border-color:rgba(0,128,0,.18);}
.ha-badge.bad{background:rgba(220,0,0,.06);border-color:rgba(220,0,0,.18);}
.ha-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px;}
.ha-mini{display:flex;flex-direction:column;gap:2px;}
.ha-mini .k{font-size:12px;opacity:.6;}
.ha-mini .v{font-size:16px;font-weight:800;}
.ha-ring{width:46px;height:46px;border-radius:999px;display:grid;place-items:center;
  background:conic-gradient(rgba(0,0,0,.55) var(--p), rgba(0,0,0,.08) 0);}
.ha-ring > div{width:36px;height:36px;border-radius:999px;background:white;display:grid;place-items:center;
  font-size:12px;font-weight:800;}



.ha-wrap{max-width:980px;width:100%;margin:0 auto;box-sizing:border-box;}
.ha-center{text-align:center;}
.ha-header{margin:6px 0 12px;}
.ha-header .ha-title{font-size:16px;}
.ha-header .ha-sub{margin-top:-2px;}

.ha-grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:10px 0 14px;}
@media (max-width:900px){.ha-grid-3{grid-template-columns:repeat(1,minmax(0,1fr));}}

.ha-card .ha-v .blue{color:var(--ha-blue);}
.ha-progress{height:10px;border-radius:999px;background:rgba(0,0,0,.06);overflow:hidden;border:1px solid rgba(0,0,0,.08);}
.ha-progress > div{height:100%;background:var(--ha-blue);border-radius:999px;}

.ha-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:10px;}
.ha-btn{display:inline-flex;align-items:center;justify-content:center;padding:8px 14px;border-radius:999px;
  border:1px solid rgba(0,0,0,.12);background:rgba(255,255,255,.85);font-weight:700;font-size:13px;}
.ha-btn.primary{background:var(--ha-blue);border-color:var(--ha-blue);color:white;}
.ha-btn:hover{filter:brightness(.98);}

.ha-switch{display:flex;justify-content:center;margin:8px 0 4px;}
/* Streamlit radio horizontal as segmented */
.ha-switch [role="radiogroup"]{background:rgba(0,0,0,.04);border:1px solid rgba(0,0,0,.08);border-radius:999px;padding:4px;gap:4px;}
.ha-switch label{margin:0 !important;}
.ha-switch div[data-baseweb="radio"]>div{display:none;}
.ha-switch div[data-baseweb="radio"]{padding:0 !important;}
.ha-switch span{font-size:12px;font-weight:800;opacity:.78;}
.ha-switch input:checked + div + span{opacity:1;}
.ha-switch input:checked + div + span{color:var(--ha-blue);}

.ha-meta{font-size:12px;opacity:.65;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.ha-tag{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;
  background:rgba(0,0,0,.04);border:1px solid rgba(0,0,0,.08);font-size:12px;opacity:.85;}
.ha-empty{opacity:.65;font-size:13px;padding:10px 4px;text-align:center;}

/* Compact top nav buttons (MyPage) */
div[data-testid="column"] .stButton button{
  border-radius:12px;
}
button[kind="secondary"], button[kind="primary"]{
  border-radius:12px;
}
</style>
        """,
        unsafe_allow_html=True,
    )

def _load_wrong_notes(limit: int = 300) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        r = sb.table("wrong_notes").select("*").order("created_at", desc=True).limit(limit).execute()
        return getattr(r, "data", None) or []
    except Exception:
        return []


def _load_attempts(limit: int = 80) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Load quiz_attempts with flexible columns. Returns (data, err_msg)."""
    sb = _sb()
    if not sb:
        return [], "로그인 후 이용 가능합니다."

    candidates = [
        "created_at,kind,level,quiz_len,score",
        "created_at,kind,level,total,correct,score",
        "created_at,kind,level,correct_count,wrong_count,score",
        "created_at,kind,level,score",
        "created_at,kind,level",
        "created_at,kind",
        "created_at",
    ]
    last_err = None
    for cols in candidates:
        try:
            r = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(limit).execute()
            data = getattr(r, "data", None) or []
            return data, None
        except Exception as e:
            last_err = e

    # last fallback
    try:
        r = sb.table("quiz_attempts").select("*").order("created_at", desc=True).limit(min(30, limit)).execute()
        data = getattr(r, "data", None) or []
        return data, None if data is not None else "학습 기록을 불러올 수 없습니다. (quiz_attempts 테이블/RLS 확인)"
    except Exception:
        return [], "학습 기록을 불러올 수 없습니다. (RLS 또는 테이블 확인)"


def _type_label(raw: str) -> str:
    m = {"word": "단어", "kanji": "한자", "talk": "회화"}
    return m.get((raw or "").lower(), (raw or "").upper() or "QUIZ")


# ---------- KPI / flow ----------
def _kpi(
    wrongs: List[Dict[str, Any]],
    attempts: List[Dict[str, Any]],
    msgs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    now = _now_utc()

    # wrongs last 7d + repeat(>=3)
    w7 = 0
    wrep = 0
    for w in wrongs:
        dt = _parse_dt(w.get("created_at"))
        if dt and (now - dt) <= timedelta(days=7):
            w7 += 1
        wc = w.get("wrong_count") or w.get("count") or w.get("mistakes")
        if isinstance(wc, (int, float)) and float(wc) >= 3:
            wrep += 1

    # average score
    scores: List[float] = []
    for a in attempts:
        sc = a.get("score")
        if isinstance(sc, (int, float)):
            scores.append(float(sc))
    avg_score = (sum(scores) / len(scores)) if scores else None

    # attempts last 7/30 days
    a7 = 0
    a30 = 0
    for a in attempts:
        dt = _parse_dt(a.get("created_at"))
        if not dt:
            continue
        if (now - dt) <= timedelta(days=7):
            a7 += 1
        if (now - dt) <= timedelta(days=30):
            a30 += 1

    # messages stats
    msgs = msgs or []
    mu = 0
    m7 = 0
    for m in msgs:
        if not m.get("read_at"):
            mu += 1
        dt = _parse_dt(m.get("created_at"))
        if dt and (now - dt) <= timedelta(days=7):
            m7 += 1

    # monthly flow target: 30회(학습 이벤트 기준)
    target = 30
    pct = max(0, min(100, int(round((a30 / target) * 100)))) if target > 0 else 0

    return {
        "wrong_total": len(wrongs),
        "wrong_7d": w7,
        "wrong_repeat": wrep,
        "avg_score": avg_score,
        "attempt_7d": a7,
        "attempt_30d": a30,
        "flow_pct": pct,
        "flow_target": target,
        "msg_total": len(msgs),
        "msg_unread": mu,
        "msg_7d": m7,
    }
def _segment_counts(wrongs: List[Dict[str, Any]]) -> Dict[str, int]:
    c = {"단어": 0, "한자": 0, "회화": 0}
    for w in wrongs:
        c[_type_label(str(w.get("quiz_type") or ""))] = c.get(_type_label(str(w.get("quiz_type") or "")), 0) + 1
    # normalize keys to ensure order
    return {"단어": c.get("단어", 0), "한자": c.get("한자", 0), "회화": c.get("회화", 0)}


def _segment_bar_html(counts: Dict[str, int]) -> str:
    total = sum(counts.values()) or 1
    w = int(round(counts.get("단어", 0) / total * 100))
    k = int(round(counts.get("한자", 0) / total * 100))
    t = max(0, 100 - w - k)
    return f"""
<div class="ha-seg" title="단어/한자/회화 비율">
  <span class="w1" style="width:{w}%;"></span>
  <span class="w2" style="width:{k}%;"></span>
  <span class="w3" style="width:{t}%;"></span>
</div>
"""


# ---------- message ----------
def _mark_message_read(msg_id: str):
    _safe_update("user_messages", {"read_at": datetime.utcnow().isoformat()}, "id", msg_id)


# ---------- components ----------
def _nav_back_and_logout():
    """Top navigation for MyPage.
    - Keep it minimal and consistent with admin-style UI (no big full-width buttons).
    - '홈' sends the user back to hub (home).
    - '로그아웃' clears auth/session keys.
    """
    # Spacer + compact buttons (aligned to the right)
    sp, b1, b2 = st.columns([6, 1.4, 1.6], vertical_alignment="center")
    with sp:
        st.markdown("""<div style="height:4px"></div>""", unsafe_allow_html=True)
    with b1:
        if st.button("🏠 홈", key="mypage_back_hub", use_container_width=True):
            st.session_state["hub_page"] = "home"
            st.rerun()
    with b2:
        if st.button("로그아웃", key="mypage_logout", use_container_width=True):
            for k in ["user", "sb_authed", "access_token", "refresh_token", "hub_page"]:
                st.session_state.pop(k, None)
            st.rerun()


def _card_open(title: str, subtitle: str = ""):
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ha-meta">{subtitle}</div>', unsafe_allow_html=True)


def _card_close():
    st.markdown("</div>", unsafe_allow_html=True)


# ---------- sections ----------
def _section_wrongs(wrongs: List[Dict[str, Any]]):
    if not wrongs:
        _card_open("📚 오답", "아직 저장된 오답 상세가 없습니다.")
        st.info("틀린 문제는 자동으로 오답카드에 쌓입니다.")
        _card_close()
        return

    counts = _segment_counts(wrongs)
    _card_open("📚 오답", "한눈에 보기 (단어/한자/회화)")
    st.markdown(_segment_bar_html(counts), unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin-top:10px; display:flex; justify-content:center; gap:10px; flex-wrap:wrap;">'
        f'<span class="ha-pill"><span class="ha-dot"></span> 단어 {counts.get("단어",0)}</span>'
        f'<span class="ha-pill"><span class="ha-dot" style="opacity:.65;"></span> 한자 {counts.get("한자",0)}</span>'
        f'<span class="ha-pill"><span class="ha-dot" style="opacity:.40;"></span> 회화 {counts.get("회화",0)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _card_close()

    # 추천 복습(반복 오답)
    key_counts: Dict[str, int] = {}
    by_key: Dict[str, Dict[str, Any]] = {}
    for w in wrongs:
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")
        qt = str(w.get("quiz_type") or "")
        k = f"{qt}||{q}||{ca}"
        key_counts[k] = key_counts.get(k, 0) + 1
        if k not in by_key:
            by_key[k] = w
    repeats = sorted(key_counts.items(), key=lambda x: (-x[1], x[0]))[:4]

    _card_open("🔥 오늘 복습 추천", "반복해서 틀린 문제부터 정리해요.")
    if repeats and repeats[0][1] >= 2:
        for k, cnt in repeats:
            w = by_key.get(k, {})
            q = str(w.get("question") or "")
            ca = str(w.get("correct_answer") or "")
            ua = str(w.get("user_answer") or "")
            qt = _type_label(str(w.get("quiz_type") or ""))
            lv = str(w.get("level") or "")
            when = _fmt_dt(w.get("created_at"))
            meta = " · ".join([p for p in [qt, lv, f"{cnt}회", when] if p])
            st.markdown('<div class="ha-card" style="border-radius:16px; box-shadow:none;">', unsafe_allow_html=True)
            st.markdown(f'<div class="ha-meta">{meta}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ha-wq">{q}</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
<div class="ha-ans">
  <div><span class="k">정답</span> <span class="ok">{ca}</span></div>
  <div><span class="k">내 답</span> <span class="bad">{ua}</span></div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("아직 반복 오답이 쌓이지 않았어요. 최근 오답을 먼저 정리해볼까요?")
    _card_close()

    # 최근 오답 카드 (compact)
    _card_open("🗂 최근 오답", "최근 10개")
    for w in wrongs[:10]:
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")
        ua = str(w.get("user_answer") or "")
        qt = _type_label(str(w.get("quiz_type") or ""))
        lv = str(w.get("level") or "")
        when = _fmt_dt(w.get("created_at"))
        meta = " · ".join([p for p in [qt, lv, when] if p])

        st.markdown('<div class="ha-card" style="border-radius:16px; box-shadow:none; padding:12px;">', unsafe_allow_html=True)
        st.markdown(f'<div class="ha-meta">{meta}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ha-wq">{q}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="ha-ans">
  <div><span class="k">정답</span> <span class="ok">{ca}</span></div>
  <div><span class="k">내 답</span> <span class="bad">{ua}</span></div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("전체 오답 (최근 30개)"):
        for w in wrongs[:30]:
            qt = _type_label(str(w.get("quiz_type") or ""))
            lv = str(w.get("level") or "")
            when = _fmt_dt(w.get("created_at"))
            q = str(w.get("question") or "")
            ca = str(w.get("correct_answer") or "")
            ua = str(w.get("user_answer") or "")
            st.markdown(f"- {when} · {qt} {('· '+lv) if lv else ''} · **{q}** / 정답 {ca} / 내답 {ua}")
    _card_close()

    _top10_block(wrongs)


def _build_mcq_choices(correct: str, pool: List[str], k: int = 4) -> List[str]:
    pool = [p for p in pool if p and p != correct]
    random.shuffle(pool)
    choices = [correct] + pool[: max(0, k - 1)]
    choices = list(dict.fromkeys(choices))
    while len(choices) < 2:
        choices.append("…")
    random.shuffle(choices)
    return choices


def _top10_block(wrongs: List[Dict[str, Any]]):
    _card_open("🧪 TOP10 재시험", "오답카드 기반으로 10문항을 다시 풀어봅니다.")
    if not wrongs:
        st.info("오답 상세 데이터가 없어서 TOP10 재시험을 시작할 수 없습니다.")
        _card_close()
        return

    # CTA row
    c1, c2 = st.columns([1.2, 1])
    with c1:
        start = st.button("TOP10 재시험 시작", type="primary", use_container_width=True, key="top10_start_btn")
    with c2:
        mode = st.selectbox("방식", ["4지선다", "단답"], index=0, key="top10_mode_sel")

    if start:
        st.session_state["top10_running"] = True
        st.session_state["top10_mode"] = mode
        st.session_state["top10_items"] = wrongs[:10]
        st.session_state["top10_answers"] = {}
        st.session_state["top10_submitted"] = False
        st.rerun()

    if st.session_state.get("top10_running") is not True:
        st.caption("원할 때만 시작하세요. 시험은 마이페이지 안에서 진행됩니다.")
        _card_close()
        return

    items: List[Dict[str, Any]] = st.session_state.get("top10_items", wrongs[:10])
    mode = st.session_state.get("top10_mode", "4지선다")
    answers: Dict[str, Any] = st.session_state.get("top10_answers", {})
    pool = [str(w.get("correct_answer") or "") for w in wrongs[:200] if w.get("correct_answer")]

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)
    for i, w in enumerate(items, start=1):
        qid = str(w.get("id") or f"q{i}")
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")
        st.markdown(f"**{i}. {q}**")

        if mode == "단답":
            answers[qid] = st.text_input("정답", value=str(answers.get(qid, "")), key=f"top10_in_{qid}")
        else:
            choices = _build_mcq_choices(ca, pool, k=4)
            default = choices.index(answers.get(qid)) if answers.get(qid) in choices else 0
            answers[qid] = st.radio("보기", choices, index=default, key=f"top10_mc_{qid}")

        if st.session_state.get("top10_submitted"):
            ua = str(answers.get(qid, "")).strip()
            if ua == ca:
                st.success("정답")
            else:
                st.error(f"정답: {ca}")
        st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    st.session_state["top10_answers"] = answers

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("제출", type="primary", use_container_width=True, key="top10_submit_btn"):
            st.session_state["top10_submitted"] = True
            st.rerun()
    with c2:
        if st.button("시험 재시작", use_container_width=True, key="top10_restart_btn"):
            st.session_state["top10_running"] = False
            st.session_state.pop("top10_items", None)
            st.session_state.pop("top10_answers", None)
            st.session_state["top10_submitted"] = False
            st.rerun()

    if st.session_state.get("top10_submitted"):
        correct = 0
        for w in items:
            qid = str(w.get("id") or "")
            ca = str(w.get("correct_answer") or "")
            ua = str(answers.get(qid, "")).strip()
            if ua == ca:
                correct += 1
        st.success(f"점수: {correct} / {len(items)}")

    _card_close()


def _section_records(attempts: List[Dict[str, Any]], err: Optional[str]):
    if err:
        _card_open("📈 학습 기록", err)
        st.info(err)
        _card_close()
        return
    if not attempts:
        _card_open("📈 학습 기록", "기록이 아직 없습니다.")
        st.info("학습을 진행하면 여기에 기록이 쌓입니다.")
        _card_close()
        return

    # Summary pills
    scores = [float(a["score"]) for a in attempts if isinstance(a.get("score"), (int, float))]
    avg = (sum(scores) / len(scores)) if scores else None
    total = len(attempts)

    _card_open("📈 학습 기록", "최근 기록 요약")
    pill_parts = [f"최근 {min(50,total)}건"]
    if avg is not None:
        pill_parts.append(f"평균 {avg:.1f}점")
    st.markdown('<div style="display:flex; justify-content:center; gap:10px; flex-wrap:wrap; margin-top:6px;">' +
                "".join([f'<span class="ha-pill">{p}</span>' for p in pill_parts]) +
                "</div>", unsafe_allow_html=True)
    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    # Compact card list (no table)
    for a in attempts[:12]:
        when = _fmt_dt(a.get("created_at"))
        kind = _type_label(str(a.get("kind") or ""))
        level = str(a.get("level") or "")
        quiz_len = a.get("quiz_len") or a.get("total") or a.get("question_count") or ""
        score = a.get("score")
        meta = " · ".join([p for p in [when, kind, level] if p])
        right = " · ".join([p for p in [f"{quiz_len}문" if quiz_len else "", f"{score}점" if score not in (None, "") else ""] if p])

        st.markdown('<div class="ha-card" style="border-radius:16px; box-shadow:none; padding:12px;">', unsafe_allow_html=True)
        st.markdown(f'<div class="ha-meta">{meta}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:6px; font-size:15px; font-weight:850; color:var(--ha-text);">{right or "기록"}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("최근 50건 더 보기"):
        for a in attempts[:50]:
            when = _fmt_dt(a.get("created_at"))
            kind = _type_label(str(a.get("kind") or ""))
            level = str(a.get("level") or "")
            quiz_len = a.get("quiz_len") or a.get("total") or a.get("question_count") or ""
            score = a.get("score")
            parts = [p for p in [when, kind, level] if p]
            if quiz_len:
                parts.append(f"{quiz_len}문")
            if score not in (None, ""):
                parts.append(f"{score}점")
            st.markdown("- " + " · ".join(parts))

    _card_close()


def _section_messages():
    msgs = _safe_select("user_messages", cols="id,title,body,created_at,read_at", limit=120)
    if not msgs:
        _card_open("📩 받은 메시지", "받은 메시지가 없습니다.")
        st.info("관리자 메시지가 도착하면 여기에 표시됩니다.")
        _card_close()
        return

    unread = [m for m in msgs if not m.get("read_at")]
    _card_open("📩 받은 메시지", "중요 공지와 안내를 확인하세요.")
    st.markdown(
        f'<div style="display:flex; justify-content:center; gap:10px; flex-wrap:wrap; margin-top:6px;">'
        f'<span class="ha-pill">전체 {len(msgs)}</span>'
        f'<span class="ha-pill"><span class="ha-dot"></span> 읽지 않음 {len(unread)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    show_unread_only = st.toggle("읽지 않은 메시지만 보기", value=False, key="msg_unread_only")
    show = unread if show_unread_only else msgs

    for m in show[:25]:
        mid = m.get("id")
        title = m.get("title") or "메시지"
        body = m.get("body") or ""
        when = _fmt_dt(m.get("created_at"))
        is_unread = not m.get("read_at")

        st.markdown('<div class="ha-card" style="border-radius:16px; box-shadow:none; padding:12px;">', unsafe_allow_html=True)
        head = f'<span class="ha-dot"></span> ' if is_unread else ''
        st.markdown(f'<div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">'
                    f'<div style="text-align:left;">{head}<span style="font-weight:850; color:var(--ha-text);">{title}</span>'
                    f'<div class="ha-meta" style="margin-top:2px;">{when}</div></div>'
                    f'</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:10px; text-align:left; color:var(--ha-text); opacity:.92; white-space:pre-wrap;">{body}</div>',
                    unsafe_allow_html=True)
        if is_unread and mid:
            if st.button("읽음 처리", key=f"msg_read_{mid}"):
                _mark_message_read(mid)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    _card_close()


# ---------- main ----------
def render():
    _css()
    user = _user()
    uid = _user_id(user)
    email = _user_email(user)

    st.markdown('<div class="ha-wrap">', unsafe_allow_html=True)

    # Header
    st.markdown(
        f"""
<div class="ha-header ha-center">
  <div class="ha-title">마이페이지</div>
  <div class="ha-sub">{email or ""}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    _nav_back_and_logout()

    # Load data once
    wrongs = _load_wrong_notes(limit=300)
    attempts, attempts_err = _load_attempts(limit=120)

    msgs = _load_messages(limit=200)
    k = _kpi(wrongs, attempts if not attempts_err else [], msgs)

    # --- KPI (A): numbers first ---
    avg_txt = f"{k['avg_score']:.0f}" if isinstance(k.get("avg_score"), (int, float)) else "—"
    st.markdown(
        f"""
<div class="ha-grid-3">
  <div class="ha-card">
    <div class="ha-k">오답</div>
    <div class="ha-v"><span class="blue">{k['wrong_total']}</span></div>
    <div class="ha-s">반복 오답 {k['wrong_repeat']} · 최근 7일 {k['wrong_7d']}</div>
  </div>
  <div class="ha-card">
    <div class="ha-k">평균 점수</div>
    <div class="ha-v">{avg_txt}<span style="font-size:16px;font-weight:800;opacity:.55;margin-left:4px;">점</span></div>
    <div class="ha-s">최근 7일 학습 {k['attempt_7d']}회</div>
  </div>
  <div class="ha-card">
    <div class="ha-k">받은 메시지</div>
    <div class="ha-v"><span class="blue">{k['msg_unread']}</span><span style="font-size:16px;font-weight:800;opacity:.55;margin-left:6px;">안 읽음</span></div>
    <div class="ha-s">전체 {k['msg_total']} · 최근 7일 {k['msg_7d']}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --- Flow (B): subtle progress, no charts ---
    st.markdown(
        f"""
<div class="ha-section">
  <div class="ha-title">이번 달 학습 흐름</div>
  <div class="ha-sub">최근 30일 {k['attempt_30d']}회 · 목표 {k['flow_target']}회</div>
  <div class="ha-progress"><div style="width:{k['flow_pct']}%;"></div></div>
  <div class="ha-sub" style="margin-top:8px;">{k['flow_pct']}% 진행 중</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # --- Switch (C): calm segmented navigation ---
    st.markdown('<div class="ha-switch">', unsafe_allow_html=True)
    section = st.radio(
        "",
        ["오답", "학습 기록", "받은 메시지"],
        horizontal=True,
        key="mypage_section",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if section == "오답":
        _section_wrongs_adminstyle(wrongs)
    elif section == "학습 기록":
        _section_records_adminstyle(attempts, attempts_err)
    else:
        _section_messages_adminstyle()

    st.markdown("</div>", unsafe_allow_html=True)

