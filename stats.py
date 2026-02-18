# stats.py
import datetime
import streamlit as st

def _ensure_attempt_log():
    if "attempt_log" not in st.session_state or not isinstance(st.session_state["attempt_log"], list):
        st.session_state["attempt_log"] = []

def log_attempt(mode: str, total: int, correct: int):
    _ensure_attempt_log()
    st.session_state["attempt_log"].append({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "mode": str(mode),
        "total": int(total),
        "correct": int(correct),
    })

def aggregate_last_7_days():
    _ensure_attempt_log()
    today = datetime.date.today()
    days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    stat = {d.isoformat(): {"total": 0, "correct": 0} for d in days}

    for a in st.session_state["attempt_log"][-500:]:
        try:
            ts = str(a.get("ts", ""))[:10]
            if ts in stat:
                stat[ts]["total"] += int(a.get("total", 0) or 0)
                stat[ts]["correct"] += int(a.get("correct", 0) or 0)
        except Exception:
            continue

    # streak
    streak = 0
    for i in range(0, 365):
        d = today - datetime.timedelta(days=i)
        k = d.isoformat()
        if k in stat and stat[k]["total"] > 0:
            streak += 1
        else:
            break

    # today stats
    tk = today.isoformat()
    today_total = stat.get(tk, {}).get("total", 0)
    today_correct = stat.get(tk, {}).get("correct", 0)

    # last score
    last_score = None
    try:
        last = st.session_state["attempt_log"][-1]
        last_score = (int(last.get("correct", 0)), int(last.get("total", 0)))
    except Exception:
        last_score = None

    return days, stat, streak, (today_total, today_correct), last_score
