from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st


# ============================================================
# ✅ My Page (Refactor B)
# - Home Hub 스타일과 톤을 맞춘 "복습 센터" UI
# - 홈허브 → 마이페이지로 올 때 돌아가기 버튼 제공
# - 오답(상세) 테이블이 있으면 카드로 표시(여러 후보 테이블 자동 탐색)
# - 메시지함(user_messages) 표시 + 읽음 처리
# - 학습 기록(quiz_attempts) 요약 + 최근 세트 리스트
# ============================================================

def _get_email(user: Any) -> Optional[str]:
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


def _dt_str(v: Any) -> str:
    s = str(v or "")
    if "T" in s:
        s = s.replace("T", " ")
    if "." in s:
        s = s.split(".")[0]
    return s


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _inject_css() -> None:
    st.markdown(
        """
<style>
/* layout */
.ha-page { max-width: 980px; margin: 0 auto; }
.ha-top {
  display:flex; align-items:flex-start; justify-content:space-between; gap:12px;
  margin: 4px 0 10px 0;
}
.ha-h1 { font-size: 1.15rem; font-weight: 900; margin: 0; }
.ha-sub { opacity: .75; margin-top: 4px; font-size: .93rem; }
.ha-actions { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.ha-chip {
  display:inline-flex; align-items:center; gap:6px;
  padding: 6px 10px; border-radius: 999px;
  background: rgba(0,0,0,.04); border: 1px solid rgba(0,0,0,.06);
  font-size: .85rem; font-weight: 700;
}

/* cards */
.ha-card {
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 16px;
  padding: 14px 16px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0,0,0,0.04);
  margin-bottom: 12px;
}
.ha-card-title { font-weight: 900; font-size: 1.02rem; margin: 0; }
.ha-card-sub { opacity:.72; margin-top: 4px; font-size: .92rem; }

.ha-metrics { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.ha-pill {
  padding: 6px 10px; border-radius: 999px;
  background: rgba(0,0,0,.04);
  border: 1px solid rgba(0,0,0,.05);
  font-weight: 800; font-size: .88rem;
}

/* wrong card list */
.ha-wrong {
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 14px;
  padding: 12px 14px;
  background: #fff;
  box-shadow: 0 6px 18px rgba(0,0,0,.04);
  margin: 10px 0;
}
.ha-wrong-top { display:flex; justify-content:space-between; align-items:center; gap:12px; }
.ha-wrong-q { font-weight: 900; }
.ha-wrong-meta { opacity:.72; font-size:.88rem; white-space:nowrap; }
.ha-wrong-body { margin-top: 8px; opacity:.92; line-height:1.45; }

/* message list */
.ha-msg { border:1px solid rgba(0,0,0,.08); border-radius:14px; padding:12px 14px; background:#fff;
  box-shadow:0 6px 18px rgba(0,0,0,.04); margin:10px 0; }
.ha-msg-top { display:flex; justify-content:space-between; align-items:center; gap:10px; }
.ha-msg-title { font-weight: 900; }
.ha-msg-date { opacity:.7; font-size:.86rem; white-space:nowrap; }
.ha-msg-body { margin-top: 8px; white-space: pre-wrap; opacity: .92; line-height: 1.5; }
</style>
""",
        unsafe_allow_html=True,
    )


def _go_home() -> None:
    # home.py routing uses hub_page + query param p
    st.session_state["hub_page"] = "home"
    try:
        st.query_params["p"] = "home"
    except Exception:
        pass
    st.rerun()


def _try_fetch_wrongs(sb: Any, email: str, limit: int = 30) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Best-effort: 여러 후보 테이블에서 '오답 상세'를 자동 탐색합니다.
    - 반환: (table_name or None, rows)
    """
    candidates = [
        ("wrong_notes", ["created_at", "level", "pos_mode", "question", "your_answer", "correct_answer", "note", "meta", "item"]),
        ("wrong_cards", ["created_at", "level", "pos_mode", "question", "user_answer", "correct_answer", "jp_word", "reading", "meaning", "extra"]),
        ("wrongs", ["created_at", "level", "pos_mode", "question", "user_answer", "correct_answer", "jp_word", "reading", "meaning"]),
        ("mistakes", ["created_at", "level", "pos_mode", "question", "user_answer", "correct_answer", "jp_word", "reading", "meaning"]),
        ("wrong_items", ["created_at", "level", "pos_mode", "question", "user_answer", "correct_answer", "jp_word", "reading", "meaning"]),
    ]

    # where column guess
    where_cols = ["user_email", "email"]

    for t, cols in candidates:
        for w in where_cols:
            try:
                # 일부 테이블은 컬럼이 없어도 에러가 날 수 있어 try
                q = sb.table(t).select(",".join(cols))
                q = q.eq(w, email)
                q = q.order("created_at", desc=True).limit(limit)
                rows = q.execute().data or []
                if rows:
                    return t, rows
            except Exception:
                continue

    return None, []


def _fetch_attempts(sb: Any, email: str, limit: int = 200) -> List[Dict[str, Any]]:
    try:
        rows = (
            sb.table("quiz_attempts")
            .select("created_at,level,pos_mode,quiz_len,score,wrong_count")
            .eq("user_email", email)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        return rows or []
    except Exception:
        return []


def _fetch_messages(sb: Any, uid: str, limit: int = 30) -> List[Dict[str, Any]]:
    try:
        rows = (
            sb.table("user_messages")
            .select("id,title,body,created_at,read_at")
            .eq("user_id", uid)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        return rows or []
    except Exception:
        return []


def _mark_message_read(sb: Any, msg_id: str) -> bool:
    try:
        sb.table("user_messages").update({"read_at": datetime.utcnow().isoformat()}).eq("id", msg_id).execute()
        return True
    except Exception:
        return False


def render() -> None:
    _inject_css()

    user = st.session_state.get("user")
    sb = st.session_state.get("sb_authed") or st.session_state.get("sb")
    email = _get_email(user) or st.session_state.get("user_email")

    uid_now = st.session_state.get("user_id") or getattr(user, "id", None)
    uid = str(uid_now) if uid_now else None

    # focus hint from hub buttons
    focus = st.session_state.get("my_focus")
    try:
        qp_my = st.query_params.get("my")
        if isinstance(qp_my, str) and qp_my:
            focus = qp_my
    except Exception:
        pass

    st.markdown('<div class="ha-page">', unsafe_allow_html=True)

    # Top header
    left, right = st.columns([0.72, 0.28], vertical_alignment="top")
    with left:
        st.markdown('<div class="ha-top">', unsafe_allow_html=True)
        st.markdown(
            """
<div>
  <div class="ha-h1">🧾 복습 · 기록 관리</div>
  <div class="ha-sub">오답을 정리하고, TOP10으로 다시 도전하세요.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="ha-actions">', unsafe_allow_html=True)
        if st.button("← 홈허브", key="my_back_home"):
            _go_home()
        # 로그아웃은 home.py가 action=logout 처리
        st.markdown('<a class="ha-chip" href="?action=logout" target="_self">🚪 로그아웃</a>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Guard
    if not sb or not email:
        st.info("로그인 정보를 불러오는 중입니다. 홈에서 다시 들어오면 자동으로 연결됩니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Pull data
    attempts = _fetch_attempts(sb, email, limit=200)
    total_attempts = len(attempts)
    total_q = sum(_safe_int(r.get("quiz_len")) for r in attempts)
    total_score = sum(_safe_int(r.get("score")) for r in attempts)
    total_wrong = sum(_safe_int(r.get("wrong_count")) for r in attempts)
    acc = int(round((total_score / total_q) * 100)) if total_q else 0

    # Overview card (email only, no plan line)
    st.markdown(
        f"""
<div class="ha-card">
  <div class="ha-card-title">{email}</div>
  <div class="ha-card-sub">내 학습 데이터를 한곳에서 정리합니다.</div>
  <div class="ha-metrics">
    <div class="ha-pill">학습 세트 {total_attempts}회</div>
    <div class="ha-pill">풀어본 문항 {total_q}문</div>
    <div class="ha-pill">정답률 {acc}%</div>
    <div class="ha-pill">오답 {total_wrong}개</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Tabs (structure B)
    tab_names = ["오답 · TOP10", "학습 기록", "받은 메시지"]
    default_idx = 0
    if focus in ("records", "log", "history"):
        default_idx = 1
    elif focus in ("inbox", "messages", "msg"):
        default_idx = 2

    tabs = st.tabs(tab_names)
    # Streamlit tabs don't accept default index directly; we use focus for UI hints inside sections.

    # 1) Wrong / Top10
    with tabs[0]:
        st.markdown(
            """
<div class="ha-card">
  <div class="ha-card-title">📚 오답카드</div>
  <div class="ha-card-sub">틀린 항목을 모아 복습합니다. (오답 상세 저장 테이블이 있으면 카드로 표시됩니다.)</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # Actions row
        a1, a2, a3 = st.columns([0.34, 0.33, 0.33])
        with a1:
            st.button("🔎 오답카드 새로고침", key="my_wrongs_refresh")
        with a2:
            # Navigate to word training (best effort)
            if st.button("🧪 TOP10 재시험", type="primary", key="my_top10_go"):
                # best-effort: 이동만 확실히
                st.session_state["hub_page"] = "word"
                try:
                    st.query_params["p"] = "word"
                    st.query_params["from"] = "top10"
                except Exception:
                    pass
                st.rerun()
        with a3:
            if st.button("➡️ 단어 훈련으로 이동", key="my_go_word"):
                st.session_state["hub_page"] = "word"
                try:
                    st.query_params["p"] = "word"
                except Exception:
                    pass
                st.rerun()

        table_name, wrong_rows = _try_fetch_wrongs(sb, email, limit=30)

        if not wrong_rows:
            st.info(
                "오답 상세 데이터를 찾지 못했습니다. (quiz_attempts에는 오답 개수만 저장될 수 있어요.)\n\n"
                "예전처럼 ‘단어/정답/내답’ 카드가 나오게 하려면, 오답 상세를 저장하는 테이블(예: wrong_notes)이 필요합니다."
            )
        else:
            st.success(f"오답 상세 테이블: {table_name} (최근 {min(len(wrong_rows), 30)}개)")
            for r in wrong_rows[:30]:
                dt = _dt_str(r.get("created_at"))
                level = str(r.get("level") or "")
                mode = str(r.get("pos_mode") or "")
                q = r.get("question") or r.get("jp_word") or r.get("item") or "오답 항목"
                ua = r.get("your_answer") or r.get("user_answer") or r.get("selected") or ""
                ca = r.get("correct_answer") or r.get("answer") or ""

                body_lines = []
                if ua or ca:
                    body_lines.append(f"내 답: {ua}")
                    body_lines.append(f"정답: {ca}")
                meaning = r.get("meaning")
                reading = r.get("reading")
                if reading:
                    body_lines.append(f"발음: {reading}")
                if meaning:
                    body_lines.append(f"뜻: {meaning}")

                body = "\n".join(body_lines) if body_lines else "상세 정보가 부족합니다."

                st.markdown(
                    f"""
<div class="ha-wrong">
  <div class="ha-wrong-top">
    <div class="ha-wrong-q">{q}</div>
    <div class="ha-wrong-meta">{level} · {mode} · {dt}</div>
  </div>
  <div class="ha-wrong-body">{body}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # 2) Attempts / history
    with tabs[1]:
        st.markdown(
            """
<div class="ha-card">
  <div class="ha-card-title">🗂️ 학습 기록</div>
  <div class="ha-card-sub">최근 학습 세트를 카드로 정리합니다.</div>
</div>
""",
            unsafe_allow_html=True,
        )

        if not attempts:
            st.write("아직 기록이 없습니다. 훈련을 시작하면 자동으로 기록이 쌓입니다.")
        else:
            for r in attempts[:20]:
                dt = _dt_str(r.get("created_at"))
                level = str(r.get("level") or "")
                mode = str(r.get("pos_mode") or "")
                qlen = _safe_int(r.get("quiz_len"))
                score = _safe_int(r.get("score"))
                wrong = _safe_int(r.get("wrong_count"))
                pct = int(round((score / qlen) * 100)) if qlen else 0

                st.markdown(
                    f"""
<div class="ha-wrong">
  <div class="ha-wrong-top">
    <div class="ha-wrong-q">{level} · {mode}</div>
    <div class="ha-wrong-meta">{dt}</div>
  </div>
  <div class="ha-metrics" style="margin-top:8px;">
    <div class="ha-pill">점수 {score}/{qlen}</div>
    <div class="ha-pill">정답률 {pct}%</div>
    <div class="ha-pill">오답 {wrong}개</div>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # 3) Inbox / messages
    with tabs[2]:
        st.markdown(
            """
<div class="ha-card">
  <div class="ha-card-title">📩 받은 메시지</div>
  <div class="ha-card-sub">관리자가 보낸 공지/독려 메시지를 확인합니다.</div>
</div>
""",
            unsafe_allow_html=True,
        )

        if not uid:
            st.info("메시지함을 열려면 사용자 ID가 필요합니다. 홈에서 다시 로그인 후 들어와 주세요.")
        else:
            msgs = _fetch_messages(sb, uid, limit=30)
            if not msgs:
                st.write("받은 메시지가 없습니다.")
            else:
                unread = sum(1 for m in msgs if not m.get("read_at"))
                st.markdown(f'<div class="ha-chip">읽지 않음 {unread}개</div>', unsafe_allow_html=True)

                for m in msgs[:30]:
                    mid = str(m.get("id") or "")
                    title = m.get("title") or "메시지"
                    body = m.get("body") or ""
                    dt = _dt_str(m.get("created_at"))
                    read_at = m.get("read_at")

                    top_cols = st.columns([0.75, 0.25])
                    with top_cols[0]:
                        st.markdown(
                            f"""
<div class="ha-msg">
  <div class="ha-msg-top">
    <div class="ha-msg-title">{title}</div>
    <div class="ha-msg-date">{dt}</div>
  </div>
  <div class="ha-msg-body">{body}</div>
</div>
""",
                            unsafe_allow_html=True,
                        )
                    with top_cols[1]:
                        if read_at:
                            st.caption("읽음")
                        else:
                            if st.button("읽음 처리", key=f"msg_read_{mid}"):
                                ok = _mark_message_read(sb, mid)
                                if ok:
                                    st.success("처리 완료")
                                    st.rerun()
                                else:
                                    st.error("처리 실패")

    st.markdown("</div>", unsafe_allow_html=True)
