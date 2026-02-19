# mypage.py
from __future__ import annotations

from datetime import datetime, date, timedelta
from collections import defaultdict

import streamlit as st

# ============================================================
# ✅ My Page (Independent)
# - no set_page_config (handled by home.py hub)
# - reads from session_state: sb_authed, user, user_plan
# - aggregates quiz_attempts across word/kanji/talk
# ============================================================

def _to_date_str(iso_ts: str) -> str | None:
    if not iso_ts:
        return None
    try:
        # expected: "2026-02-19T12:34:56.123Z" or similar
        return iso_ts[:10]
    except Exception:
        return None

def _parse_dt(iso_ts: str) -> datetime | None:
    if not iso_ts:
        return None
    try:
        s = iso_ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _compute_streak(active_dates: set[str], today: date) -> int:
    streak = 0
    d = today
    while True:
        if d.isoformat() in active_dates:
            streak += 1
            d = d - timedelta(days=1)
            continue
        break
    return streak

def _metric_row(label: str, value: str, help_text: str | None = None):
    c1, c2 = st.columns([1.2, 1.8])
    c1.markdown(f"**{label}**")
    if help_text:
        c2.markdown(f"{value}  \n<small style='opacity:.7'>{help_text}</small>", unsafe_allow_html=True)
    else:
        c2.markdown(value)

def render_mypage():
    sb = st.session_state.get("sb_authed")
    user = st.session_state.get("user")
    plan = (st.session_state.get("user_plan") or "free").lower()

    st.markdown("## 👤 마이페이지")

    if not sb or not user:
        st.warning("로그인이 필요합니다.")
        if st.button("홈으로", use_container_width=True):
            st.session_state["hub_page"] = "home"
            st.rerun()
        return

    # ---- Fetch recent attempts (cap to keep fast)
    try:
        res = (
            sb.table("quiz_attempts")
            .select("created_at, score, quiz_len, wrong_count, level, pos_mode")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        st.error("학습 기록을 불러오지 못했습니다.")
        if st.session_state.get("is_admin"):
            st.exception(e)
        return

    # ---- Aggregate
    today = date.today()
    today_key = today.isoformat()
    week_start = today - timedelta(days=6)

    total_sets = len(rows)                          # 1 row == 1 set
    total_questions = 0
    total_correct = 0
    today_sets = 0
    today_questions = 0
    today_correct = 0

    active_dates: set[str] = set()
    sets_by_day = defaultdict(int)

    for r in rows:
        d = _to_date_str(r.get("created_at"))
        if d:
            active_dates.add(d)
            sets_by_day[d] += 1

        qlen = int(r.get("quiz_len") or 0)
        sc = int(r.get("score") or 0)

        total_questions += qlen
        total_correct += sc

        if d == today_key:
            today_sets += 1
            today_questions += qlen
            today_correct += sc

    acc_total = (total_correct / total_questions) if total_questions else 0.0
    acc_today = (today_correct / today_questions) if today_questions else 0.0

    streak = _compute_streak(active_dates, today)

    # ---- Header summary
    st.markdown(
        f"""
<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin:.25rem 0 .75rem;">
  <div style="padding:.35rem .6rem;border:1px solid rgba(0,0,0,.10);border-radius:999px;background:rgba(0,0,0,.02);font-size:.9rem;">
    <b>{'✅ PRO' if plan=='pro' else '🆓 FREE'}</b>
  </div>
  <div style="padding:.35rem .6rem;border:1px solid rgba(0,0,0,.10);border-radius:999px;background:rgba(0,0,0,.02);font-size:.9rem;">
    🔥 연속 <b>{streak}</b>일
  </div>
  <div style="padding:.35rem .6rem;border:1px solid rgba(0,0,0,.10);border-radius:999px;background:rgba(0,0,0,.02);font-size:.9rem;">
    📚 총 <b>{total_sets}</b>세트
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 전체 요약")
    _metric_row("총 세트", f"{total_sets} 세트", "최근 500회까지 집계")
    _metric_row("총 정답률", f"{acc_total*100:.1f}%", f"{total_correct}/{total_questions} 문항")
    _metric_row("오늘 세트", f"{today_sets} 세트", f"오늘 정답률 {acc_today*100:.1f}%")

    st.markdown("### 📅 최근 7일")
    # Build 7-day list oldest->newest
    days = [(week_start + timedelta(days=i)).isoformat() for i in range(7)]
    lines = []
    for d in days:
        n = sets_by_day.get(d, 0)
        # simple bar using blocks
        bar = "▮" * min(n, 20)
        lines.append(f"- {d[5:]}  **{n}세트**  {bar}")
    st.markdown("\n".join(lines))

    st.markdown("### 🧾 최근 기록 (최신 20개)")
    show = rows[:20]
    if not show:
        st.info("아직 기록이 없습니다. 훈련을 시작해 주세요.")
    else:
        for r in show:
            dt = _parse_dt(r.get("created_at"))
            ts = dt.astimezone().strftime("%m/%d %H:%M") if dt else (r.get("created_at") or "")
            qlen = int(r.get("quiz_len") or 0)
            sc = int(r.get("score") or 0)
            lvl = (r.get("level") or "").strip()
            mode = (r.get("pos_mode") or "").strip()
            st.markdown(
                f"""
<div style="border:1px solid rgba(0,0,0,.08);border-radius:14px;padding:.55rem .7rem;margin:.35rem 0;background:rgba(0,0,0,.015);">
  <div style="display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap;">
    <b>{ts}</b>
    <span style="opacity:.75">{lvl} {mode}</span>
  </div>
  <div style="opacity:.9;margin-top:.15rem;">정답 <b>{sc}</b> / {qlen}  ·  정답률 <b>{(sc/qlen*100 if qlen else 0):.0f}%</b></div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("🏠 홈으로", use_container_width=True):
        st.session_state["hub_page"] = "home"
        st.rerun()
    if c2.button("🔄 새로고침", use_container_width=True):
        st.rerun()


render_mypage()
