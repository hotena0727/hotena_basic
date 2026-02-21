from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


# ============================================================
# ✅ MyPage (Refactor v6 - Polished)
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



def _kind_label(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k in ("word", "words", "noun", "vocab"):
        return "단어"
    if k in ("kanji", "hanja", "character"):
        return "한자"
    if k in ("talk", "speech", "conversation"):
        return "회화"
    # already korean?
    if kind in ("단어","한자","회화"):
        return kind
    return (kind or "기타").upper()


def _sparkline_svg(values: List[float], width: int = 240, height: int = 48) -> str:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        vals = [0.0]
    mn, mx = min(vals), max(vals)
    if mx == mn:
        mx = mn + 1.0
    # normalize
    pts = []
    for i, v in enumerate(vals):
        x = i * (width / max(1, (len(vals)-1)))
        y = height - ((v - mn) / (mx - mn) * height)
        pts.append((x, y))
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">' \
           f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="2" opacity="0.85"/>' \
           f'</svg>'


def _stacked_bar_html(parts: List[Dict[str, Any]]) -> str:
    # parts: [{"label":..., "count":...}, ...]
    total = sum(int(p.get("count", 0)) for p in parts) or 1
    segs = []
    for p in parts:
        cnt = int(p.get("count", 0))
        pct = cnt / total * 100
        label = str(p.get("label", ""))
        segs.append(
            f'<div class="ha-seg" style="width:{pct:.2f}%"><span>{label} {cnt}</span></div>'
        )
    return '<div class="ha-stack">' + "".join(segs) + '</div>'


def _css():
    st.markdown(
        """
<style>
/* ---------- layout ---------- */
.ha-wrap {max-width: 1040px; margin: 0 auto; padding-bottom: 18px;}
.ha-head {display:flex; align-items:flex-start; justify-content:space-between; gap:14px; margin: 8px 0 14px;}
.ha-title {font-size: 22px; font-weight: 900; letter-spacing: -0.2px; margin: 0;}
.ha-sub {opacity: .72; margin-top: 4px; line-height: 1.35;}

/* ---------- actions ---------- */
.ha-actions {display:flex; gap:8px; align-items:center; flex-wrap:wrap; justify-content:flex-end;}
.ha-pill button {border-radius: 999px !important; padding: .34rem .78rem !important; font-weight: 750 !important;}
.ha-pill button[kind="secondary"] {opacity: .95;}

/* ---------- KPI cards ---------- */
.ha-kpi-grid {display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 10px 0 12px;}
@media (max-width: 820px){ .ha-kpi-grid{grid-template-columns:1fr;} }
.ha-kpi {background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%); border: 1px solid #e8edf5; border-radius: 18px; padding: 14px 14px 12px; box-shadow: 0 10px 28px rgba(18,38,63,.06);}
.ha-kpi .k {font-size: 12px; opacity: .72; font-weight: 700; letter-spacing: -.1px;}
.ha-kpi .v {font-size: 24px; font-weight: 900; letter-spacing: -.4px; margin-top: 4px;}
.ha-kpi .s {font-size: 12px; opacity: .70; margin-top: 2px;}

/* ---------- cards ---------- */
.ha-card {background: #fff; border: 1px solid #e8edf5; border-radius: 18px; padding: 16px; box-shadow: 0 10px 28px rgba(18,38,63,.06);}
.ha-card + .ha-card {margin-top: 12px;}
.ha-card h4 {margin: 0 0 8px 0; font-size: 16px;}
.ha-muted {opacity: .7;}
.ha-divider {height:1px; background:#eef2f7; margin:12px 0;}

/* list items */
.ha-item {border: 1px solid #eef2f7; background: #fbfcff; border-radius: 16px; padding: 12px 12px;}
.ha-item + .ha-item {margin-top: 10px;}
.ha-item .meta {font-size:12px; opacity:.72; margin-bottom:6px;}
.ha-item .q {font-weight: 900;}
.ha-tag {display:inline-block; padding: 3px 10px; border-radius: 999px; background:#f6f8fc; border:1px solid #e8edf5; font-size:12px; margin-right:6px;}

/* charts wrapper */
.ha-chart {border:1px solid #eef2f7; background:#ffffff; border-radius: 18px; padding: 12px;}

/* Streamlit tweaks: make tabs breathe a bit */
div[data-testid="stTabs"] button {font-weight: 750;}

/* mini charts */
.ha-chart {background:#fff; border:1px solid #e8edf5; border-radius:18px; padding:14px; box-shadow: 0 10px 28px rgba(18,38,63,.06);}
.ha-stack {display:flex; width:100%; height:38px; border-radius:14px; overflow:hidden; border:1px solid #eef2f7; background:#f6f8fc;}
.ha-seg {display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; opacity:.9; border-right:1px solid rgba(255,255,255,.7);}
.ha-seg span{padding:0 8px; white-space:nowrap;}
.ha-spark {display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 12px; border:1px solid #eef2f7; border-radius:16px; background:#fbfcff;}
.ha-spark .lbl{font-size:12px; font-weight:800; opacity:.75;}
.ha-spark .val{font-size:18px; font-weight:900; line-height:1;}
</style>
        """,
        unsafe_allow_html=True,
    )


def _nav_back_and_logout():
    st.markdown('<div class="ha-actions ha-pill">', unsafe_allow_html=True)
    c1, c2 = st.columns([1,1], vertical_alignment="center")
    with c1:
        if st.button("← 홈허브", key="mypage_back_hub", help="학습 허브로 돌아가기"):
            st.session_state["hub_page"] = "home"
            st.rerun()
    with c2:
        if st.button("로그아웃", key="mypage_logout", help="로그아웃"):
            for k in ["user", "sb_authed", "access_token", "refresh_token", "hub_page"]:
                st.session_state.pop(k, None)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


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

def _kpi_cards(items: List[Dict[str, str]]):
    # items: [{"k": "라벨", "v": "값", "s": "서브"}]
    html = ['<div class="ha-kpi-grid">']
    for it in items[:3]:
        k = str(it.get("k",""))
        v = str(it.get("v",""))
        s = str(it.get("s",""))
        html.append('<div class="ha-kpi">')
        html.append(f'<div class="k">{k}</div>')
        html.append(f'<div class="v">{v}</div>')
        if s:
            html.append(f'<div class="s">{s}</div>')
        html.append('</div>')
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def _wrong_summary(wrongs: List[Dict[str, Any]]):
    if not wrongs:
        _kpi_cards([
            {"k":"오답", "v":"0", "s":""},
            {"k":"반복오답(3회+)", "v":"0", "s":""},
            {"k":"최근 7일", "v":"0", "s":""},
        ])
        return

    df = pd.DataFrame(wrongs)
    df["dt"] = df["created_at"].apply(_to_date)
    total = int(len(df))

    key = (df.get("question", "").astype(str) + "||" + df.get("correct_answer", "").astype(str))
    rep_counts = key.value_counts()
    rep3 = int((rep_counts >= 3).sum())

    last7 = 0
    if df["dt"].notna().any():
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        last7 = int((df["dt"] >= cutoff).sum())

    _kpi_cards([
        {"k":"오답", "v":f"{total:,}", "s":"최근 100개 기준"},
        {"k":"반복오답(3회+)", "v":f"{rep3:,}", "s":"같은 문제 기준"},
        {"k":"최근 7일", "v":f"{last7:,}", "s":"최근 7일 누적"},
    ])


def _wrong_cards_ui(wrongs: List[Dict[str, Any]]):
    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📚 오답 · TOP10</h4>", unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답 상세가 없습니다. (틀린 문제는 자동으로 오답카드에 쌓입니다.)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # KPIs
    _wrong_summary(wrongs)

    # prepare df
    df = pd.DataFrame(wrongs).copy()
    df["when"] = df["created_at"].apply(_format_dt)
    df["kind"] = df.get("quiz_type", "").astype(str).apply(_type_label)
    df["key"] = df.get("question", "").astype(str) + "||" + df.get("correct_answer", "").astype(str)
    rep_counts = df["key"].value_counts()
    df["rep"] = df["key"].map(rep_counts).fillna(1).astype(int)

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    # Charts + lists
    left, right = st.columns([1, 1], vertical_alignment="top")
    with left:
        st.markdown('<div class="ha-chart">', unsafe_allow_html=True)
        st.caption("오답 유형 분포")
        kind_counts = df["kind"].map(_kind_label).value_counts().rename_axis("kind").reset_index(name="count")
        parts = [{"label": r["kind"], "count": int(r["count"])} for _, r in kind_counts.iterrows()]
        st.markdown(_stacked_bar_html(parts), unsafe_allow_html=True)
        st.caption("최근 14일 오답 추이")
        ddf = df.copy()
        ddf["day"] = ddf["created_at"].apply(_to_date).dt.date
        daily = ddf.groupby("day").size().reset_index(name="count").tail(14)
        if not daily.empty:
            vals = daily["count"].tolist()
            svg = _sparkline_svg(vals)
            st.markdown(f'<div class="ha-spark"><div><div class="lbl">최근 14일</div><div class="val">{int(vals[-1])}</div></div>{svg}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        # Repeated wrongs
        rep = df[df["rep"] >= 3].sort_values(["rep", "created_at"], ascending=[False, False]).head(12)
        if not rep.empty:
            st.caption("🔥 반복오답(3회+) TOP")
            for _, w in rep.iterrows():
                meta = " · ".join([p for p in [str(w.get("kind","")), str(w.get("level") or ""), str(w.get("when",""))] if p])
                st.markdown('<div class="ha-item">', unsafe_allow_html=True)
                st.markdown(f'<div class="meta">{meta} · <span class="ha-tag">반복 {int(w.get("rep"))}회</span></div>', unsafe_allow_html=True)
                st.write(f"**{str(w.get('question') or '')}**")
                st.write(f"정답: **{w.get('correct_answer','')}**")
                st.write(f"내 답: **{w.get('user_answer','')}**")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("반복오답(3회+)이 아직 없습니다. 👍")

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)
    st.caption("최근 오답")
    for _, w in df.sort_values("created_at", ascending=False).head(20).iterrows():
        meta = " · ".join([p for p in [str(w.get("kind","")), str(w.get("level") or ""), str(w.get("when",""))] if p])
        st.markdown('<div class="ha-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="meta">{meta}</div>', unsafe_allow_html=True)
        st.write(f"**{str(w.get('question') or '')}**")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"정답: **{w.get('correct_answer','')}**")
        with c2:
            st.write(f"내 답: **{w.get('user_answer','')}**")
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
            r = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(200).execute()
            data = getattr(r, "data", None) or []
            if data:
                break
        except Exception:
            continue

    if not data:
        try:
            r = sb.table("quiz_attempts").select("*").order("created_at", desc=True).limit(200).execute()
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
    df["dt"] = df["created_at"].apply(_to_date) if "created_at" in df.columns else None
    df["kind_label"] = df["kind"].astype(str).apply(_type_label) if "kind" in df.columns else "기타"

    total = int(len(df))
    scores = pd.to_numeric(df.get("score"), errors="coerce") if "score" in df.columns else pd.Series([], dtype=float)
    avg = float(scores.dropna().mean()) if len(scores.dropna()) else None

    last7 = 0
    if df["dt"].notna().any():
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        last7 = int((df["dt"] >= cutoff).sum())

    _kpi_cards([
        {"k":"시도", "v":f"{total:,}", "s":"최근 200건 기준"},
        {"k":"평균 점수", "v":"-" if avg is None else f"{avg:.1f}", "s":"점수 컬럼 기준"},
        {"k":"최근 7일", "v":f"{last7:,}", "s":"최근 7일 누적"},
    ])

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    left, right = st.columns([1,1], vertical_alignment="top")
    with left:
        st.markdown('<div class="ha-chart">', unsafe_allow_html=True)
        st.caption("점수 추이(최근 30회)")
        if "dt" in df.columns and df["dt"].notna().any() and "score" in df.columns:
            tmp = df[["dt", "score"]].copy()
            tmp["score"] = pd.to_numeric(tmp["score"], errors="coerce")
            tmp = tmp.dropna(subset=["dt", "score"]).sort_values("dt").tail(30)
            if len(tmp) >= 2:
                vals = tmp["score"].tolist()
                svg = _sparkline_svg(vals)
                st.markdown(f'<div class="ha-spark"><div><div class="lbl">최근 30회 점수</div><div class="val">{int(vals[-1])}</div></div>{svg}</div>', unsafe_allow_html=True)
            else:
                st.caption("점수 데이터가 더 쌓이면 그래프가 표시됩니다.")
        else:
            st.caption("점수/날짜 컬럼이 없어 그래프를 표시할 수 없습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="ha-chart">', unsafe_allow_html=True)
        st.caption("유형별 시도")
        kind_counts = df["kind_label"].value_counts().rename_axis("kind").reset_index(name="count")
        parts = [{"label": _kind_label(k), "count": int(kind_counts.loc[k, "count"])} for k in kind_counts.index]
        st.markdown(_stacked_bar_html(parts), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    st.caption("최근 기록")
    for d in df.sort_values("created_at", ascending=False).head(12).to_dict("records"):
        when = _format_dt(d.get("created_at"))
        kind = _type_label(str(d.get("kind") or ""))
        level = str(d.get("level") or "")
        quiz_len = d.get("quiz_len") or d.get("total") or d.get("question_count") or d.get("n_questions") or ""
        score = d.get("score")

        tags = []
        if kind: tags.append(kind)
        if level: tags.append(level)
        if quiz_len: tags.append(f"{quiz_len}문")
        if score not in (None, ""): tags.append(f"{score}점")

        st.markdown('<div class="ha-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="meta">{when}</div>', unsafe_allow_html=True)
        st.write(" · ".join([t for t in tags if t]))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _messages_ui():
    sb = _sb()
    uid = _user_id()

    st.markdown('<div class="ha-card">', unsafe_allow_html=True)
    st.markdown("<h4>📩 받은 메시지</h4>", unsafe_allow_html=True)

    if not sb or not uid:
        st.info("로그인 후 이용 가능합니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    try:
        r = sb.table("user_messages").select("*").order("created_at", desc=True).limit(200).execute()
        msgs = getattr(r, "data", None) or []
    except Exception:
        st.info("메시지함을 불러올 수 없습니다. (user_messages 테이블/RLS 확인)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if not msgs:
        st.info("받은 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = pd.DataFrame(msgs)
    df["dt"] = df["created_at"].apply(_to_date)
    unread = int(df["read_at"].isna().sum()) if "read_at" in df.columns else 0

    last7 = 0
    if df["dt"].notna().any():
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        last7 = int((df["dt"] >= cutoff).sum())

    _kpi_cards([
        {"k":"전체", "v":f"{len(df):,}", "s":"최근 200건 기준"},
        {"k":"읽지 않음", "v":f"{unread:,}", "s":"안 읽은 메시지"},
        {"k":"최근 7일", "v":f"{last7:,}", "s":"최근 7일 누적"},
    ])

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    left, right = st.columns([1,1], vertical_alignment="top")
    with left:
        st.markdown('<div class="ha-chart">', unsafe_allow_html=True)
        st.caption("최근 14일 메시지 수")
        ddf = df.copy()
        ddf["day"] = ddf["dt"].dt.date
        daily = ddf.groupby("day").size().reset_index(name="count").tail(14)
        if not daily.empty:
            vals = daily["count"].tolist()
            svg = _sparkline_svg(vals)
            st.markdown(f'<div class="ha-spark"><div><div class="lbl">최근 14일</div><div class="val">{int(vals[-1])}</div></div>{svg}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="ha-chart">', unsafe_allow_html=True)
        st.caption("읽지 않은 메시지만 보기")
        only_unread = st.toggle("읽지 않은 메시지만", value=False, key="mypage_msg_only_unread")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ha-divider"></div>', unsafe_allow_html=True)

    show = df
    if only_unread and "read_at" in show.columns:
        show = show[show["read_at"].isna()]

    for m in show.sort_values("created_at", ascending=False).head(20).to_dict("records"):
        title = str(m.get("title") or "메시지")
        body = str(m.get("body") or "")
        when = _format_dt(m.get("created_at"))
        is_unread = (m.get("read_at") in (None, ""))

        st.markdown('<div class="ha-item">', unsafe_allow_html=True)
        badge = '· <span class="ha-tag">읽지 않음</span>' if is_unread else ""
        st.markdown(f'<div class="meta">{when} {badge}</div>', unsafe_allow_html=True)
        st.write(f"**{title}**")
        st.write(body)
        if is_unread:
            if st.button("읽음 처리", key=f"msg_read_{m.get('id')}"):
                _mark_message_read(str(m.get("id")))
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

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
