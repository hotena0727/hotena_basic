from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


# ============================================================
# ✅ MyPage (Refactor v5 - Pretty)
# - HomeHub style, but less "dev" and more dashboard-like
# - Tabs: 오답·TOP10 / 학습 기록 / 받은 메시지
# - Charts: uses Streamlit built-ins (no custom colors)
# - wrong_notes + quiz_attempts + user_messages
# ============================================================


def _sb() -> Any:
    """Return authed Supabase client if available.

    Assumes home.py stores:
      - st.session_state['sb_authed'] or ['sb']
      - st.session_state['access_token']
    """
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
/* ---------- layout ---------- */
.ha-wrap {max-width: 1040px; margin: 0 auto; padding-bottom: 18px;}
.ha-head {display:flex; align-items:flex-start; justify-content:space-between; gap:14px; margin: 6px 0 12px;}
.ha-title {font-size: 22px; font-weight: 850; letter-spacing: -0.2px; margin: 0;}
.ha-sub {opacity: .72; margin-top: 4px;}

/* ---------- actions ---------- */
.ha-actions {display:flex; gap:8px; align-items:center; flex-wrap:wrap;}
.ha-pill button {border-radius: 999px !important; padding: .38rem .84rem !important; font-weight: 650 !important;}

/* ---------- cards ---------- */
.ha-card {background: #fff; border: 1px solid #e8edf5; border-radius: 16px; padding: 16px; box-shadow: 0 10px 28px rgba(18,38,63,.06);}
.ha-card + .ha-card {margin-top: 12px;}
.ha-card h4 {margin: 0 0 6px 0; font-size: 16px;}
.ha-muted {opacity: .7;}
.ha-row {display:flex; gap:10px; flex-wrap:wrap; align-items:center;}
.ha-badge {display:inline-block; padding: 3px 10px; border-radius: 999px; background:#f6f8fc; border:1px solid #e8edf5; font-size:12px;}
.ha-divider {height:1px; background:#eef2f7; margin:12px 0;}

/* list items */
.ha-item {border: 1px solid #eef2f7; background: #fbfcff; border-radius: 14px; padding: 12px 12px;}
.ha-item + .ha-item {margin-top: 10px;}

/* emphasis */
.ha-wrong {font-weight: 800;}
.ha-correct {font-weight: 800;}

/* Streamlit tweaks */
div[data-testid="stMetric"] {background: #fbfcff; border: 1px solid #eef2f7; border-radius: 14px; padding: 10px 12px;}
</style>
        """,
        unsafe_allow_html=True,
    )


def _nav_back_and_logout():
    left, right = st.columns([1, 1], vertical_alignment="center")
    with left:
        if st.button("← 홈허브", key="mypage_back_hub", use_container_width=True):
            st.session_state["hub_page"] = "home"
            st.rerun()
    with right:
        if st.button("로그아웃", key="mypage_logout", use_container_width=True):
            for k in ["user", "sb_authed", "access_token", "refresh_token", "hub_page"]:
                st.session_state.pop(k, None)
            st.rerun()


def _safe_select(table: str, cols: str = "*", limit: int = 200) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        r = sb.table(table).select(cols).order("created_at", desc=True).limit(limit).execute()
        return getattr(r, "data", None) or []
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


def _load_wrong_notes(limit: int = 300) -> List[Dict[str, Any]]:
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
    s = str(v)
    return s.replace("T", " ")[:16]


def _to_date(v: Any) -> Optional[pd.Timestamp]:
    if not v:
        return None
    try:
        return pd.to_datetime(v)
    except Exception:
        return None


def _type_label(kind_raw: str) -> str:
    m = {"word": "단어", "kanji": "한자", "talk": "회화"}
    k = (kind_raw or "").strip().lower()
    return m.get(k, (kind_raw or "").upper() or "기타")


def _wrong_summary(wrongs: List[Dict[str, Any]]):
    if not wrongs:
        c1, c2, c3 = st.columns(3)
        c1.metric("오답", "0")
        c2.metric("반복오답(3회+)", "0")
        c3.metric("최근 7일", "0")
        return

    df = pd.DataFrame(wrongs)
    df["dt"] = df["created_at"].apply(_to_date)
    df["kind"] = df.get("quiz_type", "").astype(str).apply(_type_label)

    total = len(df)
    # repeated by question+correct (rough but practical)
    key = (df.get("question", "").astype(str) + "||" + df.get("correct_answer", "").astype(str))
    rep_counts = key.value_counts()
    rep3 = int((rep_counts >= 3).sum())

    last7 = 0
    if df["dt"].notna().any():
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        last7 = int((df["dt"] >= cutoff).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("오답", f"{total}")
    c2.metric("반복오답(3회+)", f"{rep3}")
    c3.metric("최근 7일", f"{last7}")

    # type breakdown chart
    counts = df["kind"].value_counts().sort_values(ascending=False)
    if len(counts) >= 2:
        st.caption("오답 유형 분포")
        st.bar_chart(counts)


def _wrong_cards_ui(wrongs: List[Dict[str, Any]]):
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📚 오답카드</h4>", unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답 상세가 없습니다. (틀린 문제는 자동으로 오답카드에 쌓입니다.)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    _wrong_summary(wrongs)
    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    # highlight repeated wrongs (top)
    df = pd.DataFrame(wrongs)
    df["key"] = df.get("question", "").astype(str) + "||" + df.get("correct_answer", "").astype(str)
    rep_counts = df["key"].value_counts()
    rep_keys = set(rep_counts[rep_counts >= 3].head(10).index.tolist())

    if rep_keys:
        with st.expander("🔥 반복오답(3회 이상) 먼저 보기", expanded=False):
            top = df[df["key"].isin(rep_keys)].copy()
            top["rep"] = top["key"].map(rep_counts)
            top = top.sort_values(["rep", "created_at"], ascending=[False, False]).head(15)
            for _, w in top.iterrows():
                qt = _type_label(str(w.get("quiz_type") or ""))
                when = _format_dt(w.get("created_at"))
                q = str(w.get("question") or "")
                ca = str(w.get("correct_answer") or "")
                ua = str(w.get("user_answer") or "")
                repn = int(w.get("rep") or 0)
                st.markdown('<div class="ha-item">', unsafe_allow_html=True)
                st.caption(f"{qt} · {when} · 반복 {repn}회")
                st.write(f"**{q}**")
                st.write(f"정답: **{ca}**")
                st.write(f"내 답: **{ua}**")
                st.markdown("</div>", unsafe_allow_html=True)

    # latest list
    st.caption("최근 오답")
    for w in wrongs[:25]:
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")
        ua = str(w.get("user_answer") or "")
        qt = _type_label(str(w.get("quiz_type") or ""))
        lv = str(w.get("level") or "")
        when = _format_dt(w.get("created_at"))

        meta = " · ".join([p for p in [qt, lv, when] if p])
        st.markdown('<div class="ha-item">', unsafe_allow_html=True)
        st.caption(meta)
        st.write(f"**{q}**")
        cols = st.columns([1, 1])
        with cols[0]:
            st.write(f"정답: **{ca}**")
        with cols[1]:
            st.write(f"내 답: **{ua}**")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _build_mcq_choices(correct: str, pool: List[str], k: int = 4) -> List[str]:
    pool = [p for p in pool if p and p != correct]
    random.shuffle(pool)
    choices = [correct] + pool[: max(0, k - 1)]
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
            mode = st.selectbox("문항 방식", ["4지선다", "단답"], index=0, key="top10_mode_sel")
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
    all_correct_answers = [str(w.get("correct_answer") or "") for w in wrongs[:300] if w.get("correct_answer")]

    st.caption("오답카드에 저장된 정답을 기준으로 다시 풀어봅니다.")
    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    for i, w in enumerate(items, start=1):
        qid = str(w.get("id") or f"q{i}")
        q = str(w.get("question") or "")
        ca = str(w.get("correct_answer") or "")

        st.markdown(f"**{i}. {q}**")
        if mode == "단답":
            answers[qid] = st.text_input("정답 입력", value=str(answers.get(qid, "")), key=f"top10_in_{qid}")
        else:
            choices = _build_mcq_choices(ca, all_correct_answers, k=4)
            default = choices.index(answers.get(qid)) if answers.get(qid) in choices else 0
            answers[qid] = st.radio("보기", choices, index=default, key=f"top10_mc_{qid}")

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

    data: List[Dict[str, Any]] = []
    for cols in candidates:
        try:
            r = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(150).execute()
            data = getattr(r, "data", None) or []
            break
        except Exception:
            continue

    if not data:
        # last resort
        try:
            r = sb.table("quiz_attempts").select("*").order("created_at", desc=True).limit(100).execute()
            data = getattr(r, "data", None) or []
        except Exception:
            st.info("학습 기록을 불러올 수 없습니다. (quiz_attempts 테이블/RLS 확인)")
            st.markdown("</div>", unsafe_allow_html=True)
            return

    if not data:
        st.info("기록이 아직 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = pd.DataFrame(data)
    if "created_at" in df.columns:
        df["dt"] = df["created_at"].apply(_to_date)
    else:
        df["dt"] = None

    if "kind" in df.columns:
        df["kind_label"] = df["kind"].astype(str).apply(_type_label)
    else:
        df["kind_label"] = "기타"

    # metrics
    total = len(df)
    scores = pd.to_numeric(df.get("score"), errors="coerce") if "score" in df.columns else pd.Series([], dtype=float)
    avg = float(scores.dropna().mean()) if len(scores.dropna()) else None

    last7 = 0
    if df["dt"].notna().any():
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        last7 = int((df["dt"] >= cutoff).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("시도", f"{total}")
    c2.metric("평균 점수", "-" if avg is None else f"{avg:.1f}")
    c3.metric("최근 7일", f"{last7}")

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    # charts
    if "dt" in df.columns and df["dt"].notna().any() and "score" in df.columns:
        tmp = df[["dt", "score"]].copy()
        tmp["score"] = pd.to_numeric(tmp["score"], errors="coerce")
        tmp = tmp.dropna(subset=["dt", "score"]).sort_values("dt")
        if len(tmp) >= 2:
            st.caption("점수 추이")
            st.line_chart(tmp.set_index("dt")["score"])

    # kind breakdown
    kind_counts = df["kind_label"].value_counts().sort_values(ascending=False)
    if len(kind_counts) >= 1:
        st.caption("유형별 시도")
        st.bar_chart(kind_counts)

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    # compact list
    st.caption("최근 기록")
    for d in df.head(15).to_dict("records"):
        when = _format_dt(d.get("created_at"))
        kind = _type_label(str(d.get("kind") or ""))
        level = str(d.get("level") or "")
        quiz_len = d.get("quiz_len") or d.get("total") or d.get("question_count") or ""
        score = d.get("score")

        parts = [p for p in [when, kind, level] if p]
        if quiz_len:
            parts.append(f"{quiz_len}문")
        if score not in (None, ""):
            parts.append(f"{score}점")

        st.markdown('<div class="ha-item">', unsafe_allow_html=True)
        st.write(" · ".join(parts))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _messages_ui():
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📩 받은 메시지</h4>", unsafe_allow_html=True)

    msgs = _safe_select("user_messages", cols="id,title,body,created_at,read_at", limit=200)
    if not msgs:
        st.info("받은 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = pd.DataFrame(msgs)
    df["dt"] = df["created_at"].apply(_to_date)
    unread = int((df.get("read_at").isna() if "read_at" in df.columns else 0).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("전체", f"{len(df)}")
    c2.metric("읽지 않음", f"{unread}")
    last7 = 0
    if df["dt"].notna().any():
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        last7 = int((df["dt"] >= cutoff).sum())
    c3.metric("최근 7일", f"{last7}")

    # chart by day
    if df["dt"].notna().any():
        s = df.dropna(subset=["dt"]).copy()
        s["day"] = s["dt"].dt.date
        per_day = s.groupby("day").size()
        if len(per_day) >= 2:
            st.caption("메시지 수 (일별)")
            st.line_chart(per_day)

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    # list
    for m in msgs[:25]:
        mid = m.get("id")
        title = m.get("title") or "메시지"
        body = m.get("body") or ""
        when = _format_dt(m.get("created_at"))
        is_unread = not m.get("read_at")

        label = ("🆕 " if is_unread else "") + f"{title}  ·  {when}"
        with st.expander(label, expanded=False):
            st.write(body)
            if is_unread and mid:
                if st.button("읽음 처리", key=f"msg_read_{mid}"):
                    _mark_message_read(mid)
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render():
    _css()
    user = _user()
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

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["오답 · TOP10", "학습 기록", "받은 메시지"])

    with tab1:
        wrongs = _load_wrong_notes(limit=500)
        _wrong_cards_ui(wrongs)
        _top10_quiz_ui(wrongs)

    with tab2:
        _records_ui()

    with tab3:
        _messages_ui()

    st.markdown("</div>", unsafe_allow_html=True)
