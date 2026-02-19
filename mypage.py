# mypage.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from collections import defaultdict

import streamlit as st

# ============================================================
# ✅ Theme (Hotena) - one-time CSS inject
# ============================================================
try:
    import theme_hotena
    theme_hotena.apply_hotena_theme()
except Exception:
    pass


import pandas as pd

# NOTE:
# - Page config / global UI (floating menu, plan badge, CSS) is handled by home.py.
# - This page is fully independent (does NOT run app.py / kanji UI).

KST = timezone(timedelta(hours=9))

def _parse_created_at(v: str | None) -> datetime | None:
    if not v:
        return None
    # Supabase commonly returns ISO8601 with 'Z' or offset
    try:
        if v.endswith("Z"):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromisoformat(v)
    except Exception:
        return None

def _kst_date(dt: datetime) -> date:
    return dt.astimezone(KST).date()

def _today_start_utc_iso() -> str:
    now_kst = datetime.now(KST)
    start_kst = datetime(now_kst.year, now_kst.month, now_kst.day, 0, 0, 0, tzinfo=KST)
    start_utc = start_kst.astimezone(timezone.utc)
    # Supabase filter accepts ISO string
    return start_utc.isoformat()

def _fetch_attempts(sb, user_id: str, limit: int = 500):
    try:
        res = (
            sb.table("quiz_attempts")
            .select("created_at, quiz_len, score, level, pos_mode, wrong_count")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        st.error("학습 기록을 불러오지 못했습니다.")
        st.exception(e)
        return []

def render_mypage():
    st.markdown("## 👤 마이페이지")

    sb = st.session_state.get("sb_authed")
    user = st.session_state.get("user")

    if not sb or not user:
        st.info("로그인이 필요합니다.")
        return

    rows = _fetch_attempts(sb, user.id, limit=500)
    if not rows:
        st.info("아직 학습 기록이 없습니다. ☰ 메뉴에서 훈련을 시작해 주세요.")
        return

    # Aggregate (sets = attempts)
    total_sets = len(rows)
    total_q = sum(int(r.get("quiz_len") or 0) for r in rows)
    total_correct = sum(int(r.get("score") or 0) for r in rows)
    total_acc = (total_correct / total_q) if total_q else 0.0

    # Today (KST day)
    today_start_utc = _today_start_utc_iso()
    today_rows = [r for r in rows if (r.get("created_at") or "") >= today_start_utc]
    today_sets = len(today_rows)
    today_q = sum(int(r.get("quiz_len") or 0) for r in today_rows)
    today_correct = sum(int(r.get("score") or 0) for r in today_rows)
    today_acc = (today_correct / today_q) if today_q else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("총 세트", f"{total_sets}")
    c2.metric("오늘 세트", f"{today_sets}")
    c3.metric("전체 정답률", f"{round(total_acc*100)}%")

    st.markdown("### 📌 오늘 요약")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("오늘 문항", f"{today_q}")
    cc2.metric("오늘 정답률", f"{round(today_acc*100)}%")
    cc3.metric("최근 기록", f"{_parse_created_at(rows[0].get('created_at')).astimezone(KST).strftime('%m/%d %H:%M') if _parse_created_at(rows[0].get('created_at')) else '-'}")

    # Last 7 days sets trend
    by_day = defaultdict(lambda: {"sets": 0, "q": 0, "correct": 0})
    for r in rows:
        dt = _parse_created_at(r.get("created_at"))
        if not dt:
            continue
        d = _kst_date(dt).isoformat()
        by_day[d]["sets"] += 1
        q = int(r.get("quiz_len") or 0)
        s = int(r.get("score") or 0)
        by_day[d]["q"] += q
        by_day[d]["correct"] += s

    # build recent 7 days list (including today)
    today_kst = datetime.now(KST).date()
    days = [(today_kst - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    sets_series = [by_day[d]["sets"] for d in days]

    st.markdown("### 📅 최근 7일 학습(세트)")
    chart_df = pd.DataFrame({"날짜": days, "세트": sets_series}).set_index("날짜")
    st.bar_chart(chart_df)

    # Recent 20 attempts table (compact)
    st.markdown("### 🧾 최근 20개 기록")
    recent = rows[:20]
    table = []
    for r in recent:
        dt = _parse_created_at(r.get("created_at"))
        t = dt.astimezone(KST).strftime("%m/%d %H:%M") if dt else "-"
        q = int(r.get("quiz_len") or 0)
        s = int(r.get("score") or 0)
        acc = f"{round((s/q)*100)}%" if q else "-"
        mode = (r.get("pos_mode") or "").strip()
        lvl = (r.get("level") or "").strip()
        table.append({"시간": t, "모드": mode, "레벨": lvl, "점수": f"{s}/{q}", "정답률": acc})

    st.dataframe(table, use_container_width=True, hide_index=True)

render_mypage()
