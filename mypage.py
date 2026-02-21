from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st


# ============================================================
# ✅ MyPage (Refactor v3)
# - HomeHub style cards
# - Tabs: 오답·TOP10 / 학습 기록 / 받은 메시지
# - No top "admin message" summary (messages only in tab)
# - Uses wrong_notes table for detailed wrong cards + TOP10 test
# ============================================================


def _sb() -> Any:
    # 홈허브 로그인 세션(access_token)이 있으면 PostgREST 요청에 JWT를 붙여서 RLS 통과
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


def _css():
    st.markdown(
        """
<style>
/* page */
.ha-wrap {max-width: 980px; margin: 0 auto;}
.ha-head {display:flex; align-items:center; justify-content:space-between; gap:12px; margin: 6px 0 12px;}
.ha-title {font-size: 22px; font-weight: 800; margin: 0;}
.ha-sub {opacity: .75; margin-top: 4px;}

/* pills */
.ha-actions {display:flex; gap:8px; align-items:center; flex-wrap:wrap;}
.ha-pill button {border-radius: 999px !important; padding: .35rem .75rem !important;}
/* cards */
.ha-card {background: #fff; border: 1px solid #e8edf5; border-radius: 14px; padding: 14px 14px; box-shadow: 0 6px 18px rgba(18,38,63,.04);}
.ha-card + .ha-card {margin-top: 10px;}
.ha-card h4 {margin: 0 0 6px 0; font-size: 16px;}
.ha-muted {opacity: .7;}
.ha-row {display:flex; gap:10px; flex-wrap:wrap; align-items:center;}
.ha-badge {display:inline-block; padding: 2px 8px; border-radius: 999px; background:#f4f7fb; border:1px solid #e8edf5; font-size:12px;}
.ha-wrong {color:#c0392b; font-weight:700;}
.ha-correct {color:#2e7d32; font-weight:700;}
.ha-divider {height:1px; background:#eef2f7; margin:10px 0;}
</style>
        """,
        unsafe_allow_html=True,
    )


def _nav_back_and_logout():
    # Keep visual balance: two pill buttons with same style.
    left, right = st.columns([1, 1], vertical_alignment="center")
    with left:
        if st.button("← 홈허브", key="mypage_back_hub", use_container_width=True):
            st.session_state["hub_page"] = "home"
            st.rerun()
    with right:
        if st.button("로그아웃", key="mypage_logout", use_container_width=True):
            # rely on existing logout handler in home.py if present
            # minimal: clear session
            for k in ["user", "sb_authed", "access_token", "refresh_token", "hub_page"]:
                if k in st.session_state:
                    st.session_state.pop(k, None)
            st.rerun()


def _safe_select(table: str, cols: str = "*", limit: int = 200) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        r = sb.table(table).select(cols).order("created_at", desc=True).limit(limit).execute()
        data = getattr(r, "data", None)
        return data or []
    except Exception:
        return []


def _mark_message_read(msg_id: str):
    sb = _sb()
    if not sb:
        return
    try:
        sb.table("user_messages").update({"read_at": datetime.utcnow().isoformat()}).eq("id", msg_id).execute()
    except Exception:
        pass


def _load_wrong_notes(limit: int = 200) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        r = sb.table("wrong_notes").select("*").order("created_at", desc=True).limit(limit).execute()
        return getattr(r, "data", None) or []
    except Exception:
        return []


def _format_dt(v: Any) -> str:
    if not v:
        return ""
    try:
        # Supabase returns ISO string
        s = str(v)
        return s.replace("T", " ")[:16]
    except Exception:
        return str(v)


def _wrong_cards_ui(wrongs: List[Dict[str, Any]]):
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📚 오답카드</h4>", unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답 상세가 없습니다. (틀린 문제는 자동으로 오답카드에 쌓입니다.)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    type_map = {"word": "단어", "kanji": "한자", "talk": "회화"}
    total = len(wrongs)

    st.caption(f"총 {total}개 · 최근 {min(30, total)}개 표시")
    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    for w in wrongs[:30]:
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")
        ua = str(w.get("user_answer") or "")
        qt_raw = str(w.get("quiz_type") or "")
        qt = type_map.get(qt_raw.lower(), qt_raw.upper() or "퀴즈")
        lv = str(w.get("level") or "")
        when = _format_dt(w.get("created_at"))

        meta_parts = [qt]
        if lv:
            meta_parts.append(lv)
        if when:
            meta_parts.append(when)

        st.markdown('<div class="ha-card" style="box-shadow:none; padding:12px; border-radius:12px;">', unsafe_allow_html=True)
        st.caption(" · ".join(meta_parts))
        st.markdown(
            f"""
<div style="margin-top:6px; font-size:15px;">
  <div><span class="ha-muted">문제</span> <b>{q}</b></div>
  <div style="margin-top:4px;"><span class="ha-muted">정답</span> <span class="ha-correct">{ca}</span></div>
  <div style="margin-top:2px;"><span class="ha-muted">내 답</span> <span class="ha-wrong">{ua}</span></div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _build_mcq_choices(correct: str, pool: List[str], k: int = 4) -> List[str]:
    pool = [p for p in pool if p and p != correct]
    random.shuffle(pool)
    choices = [correct] + pool[: max(0, k - 1)]
    # if insufficient distractors, pad with blanks? better: de-dup and maybe shrink
    choices = list(dict.fromkeys(choices))
    while len(choices) < 2:
        choices.append("…")
    random.shuffle(choices)
    return choices


def _top10_quiz_ui(wrongs: List[Dict[str, Any]]):
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>🧪 TOP10 재시험</h4>", unsafe_allow_html=True)
    if not wrongs:
        st.info("오답 상세 데이터가 없어서 TOP10 재시험을 시작할 수 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if st.session_state.get("top10_running") is not True:
        c1, c2 = st.columns([1, 1])
        with c1:
            start = st.button("TOP10 재시험 시작", type="primary", use_container_width=True, key="top10_start_btn")
        with c2:
            mode = st.selectbox(
                "문항 방식",
                ["4지선다", "단답"],
                index=0,
                key="top10_mode_sel",
                help="오답카드에 저장된 ‘정답’ 기준으로 다시 풀어봅니다.",
            )
        if start:
            st.session_state["top10_running"] = True
            st.session_state["top10_mode"] = mode
            st.session_state["top10_items"] = wrongs[:10]
            st.session_state["top10_answers"] = {}
            st.session_state["top10_submitted"] = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    items: List[Dict[str, Any]] = st.session_state.get("top10_items", wrongs[:10])
    mode = st.session_state.get("top10_mode", "4지선다")
    answers: Dict[str, Any] = st.session_state.get("top10_answers", {})
    all_correct_answers = [str(w.get("correct_answer") or "") for w in wrongs[:200] if w.get("correct_answer")]

    for i, w in enumerate(items, start=1):
        qid = str(w.get("id") or f"q{i}")
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")
        st.markdown(f"**{i}. {q}**")
        if mode == "단답":
            answers[qid] = st.text_input("정답", value=str(answers.get(qid, "")), key=f"top10_in_{qid}")
        else:
            choices = _build_mcq_choices(ca, all_correct_answers, k=4)
            default = choices.index(answers.get(qid)) if answers.get(qid) in choices else 0
            answers[qid] = st.radio("보기", choices, index=default, key=f"top10_mc_{qid}")
        st.caption(f"정답: {ca}")

        st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    st.session_state["top10_answers"] = answers

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("제출", type="primary", use_container_width=True, key="top10_submit_btn"):
            st.session_state["top10_submitted"] = True
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

    st.markdown("</div>", unsafe_allow_html=True)


def _records_ui():
    sb = _sb()
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📊 학습 기록</h4>", unsafe_allow_html=True)

    if not sb:
        st.info("로그인 후 이용 가능합니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    candidates = [
        "created_at,kind,level,quiz_len,score",
        "created_at,kind,level,total,correct,score",
        "created_at,kind,level,correct_count,wrong_count,score",
        "created_at,kind,level,score",
        "created_at,kind,level",
        "created_at,kind",
        "created_at",
    ]

    data = []
    last_err = None

    for cols in candidates:
        try:
            r = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(50).execute()
            data = getattr(r, "data", None) or []
            last_err = None
            break
        except Exception as e:
            last_err = e

    if last_err is not None:
        try:
            r = sb.table("quiz_attempts").select("*").order("created_at", desc=True).limit(30).execute()
            data = getattr(r, "data", None) or []
        except Exception:
            st.info("학습 기록을 불러올 수 없습니다. (quiz_attempts 테이블/RLS/컬럼 확인)")
            st.markdown("</div>", unsafe_allow_html=True)
            return

    if not data:
        st.info("기록이 아직 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total = len(data)
    scores = []
    for d in data:
        sc = d.get("score")
        if isinstance(sc, (int, float)):
            scores.append(float(sc))
    avg = (sum(scores) / len(scores)) if scores else None
    if avg is None:
        st.caption(f"최근 {total}건")
    else:
        st.caption(f"최근 {total}건 · 평균 점수 {avg:.1f}")

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    type_map = {"word": "단어", "kanji": "한자", "talk": "회화"}
    for d in data[:15]:
        when = _format_dt(d.get("created_at"))
        kind_raw = str(d.get("kind") or "")
        kind = type_map.get(kind_raw.lower(), kind_raw.upper() or "QUIZ")
        level = str(d.get("level") or "")
        quiz_len = d.get("quiz_len") or d.get("total") or d.get("question_count") or ""
        score = d.get("score")
        parts = [p for p in [when, kind, level] if p]
        if quiz_len:
            parts.append(f"{quiz_len}문")
        if score is not None and score != "":
            parts.append(f"{score}점")
        st.markdown("- " + " · ".join(parts))

    st.markdown("</div>", unsafe_allow_html=True)


def _messages_ui():
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📩 받은 메시지</h4>", unsafe_allow_html=True)

    msgs = _safe_select("user_messages", cols="id,title,body,created_at,read_at", limit=100)
    if not msgs:
        st.info("받은 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    unread = [m for m in msgs if not m.get("read_at")]
    st.markdown(f'<div class="ha-row"><span class="ha-badge">읽지 않음 {len(unread)}개</span><span class="ha-badge">최근 {min(20,len(msgs))}개 표시</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    for m in msgs[:20]:
        mid = m.get("id")
        title = m.get("title") or "메시지"
        body = m.get("body") or ""
        when = _format_dt(m.get("created_at"))
        is_unread = not m.get("read_at")
        with st.expander(("🆕 " if is_unread else "") + f"{title}  ·  {when}", expanded=False):
            st.write(body)
            if is_unread and mid:
                if st.button("읽음 처리", key=f"msg_read_{mid}"):
                    _mark_message_read(mid)
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render():
    _css()
    user = _user()
    uid = _user_id(user)
    email = _user_email(user)

    st.markdown('<div class="ha-wrap">', unsafe_allow_html=True)

    # Header
    st.markdown(
        f"""
<div class="ha-head">
  <div>
    <div class="ha-title">🧾 복습 · 기록 관리</div>
    <div class="ha-sub">{email or ""}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    _nav_back_and_logout()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["오답 · TOP10", "학습 기록", "받은 메시지"])

    with tab1:
        wrongs = _load_wrong_notes(limit=300)
        _wrong_cards_ui(wrongs)
        _top10_quiz_ui(wrongs)

    with tab2:
        _records_ui()

    with tab3:
        _messages_ui()

    st.markdown("</div>", unsafe_allow_html=True)
