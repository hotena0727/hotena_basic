

# home.py (V37 integrated router - embedded word app)
from __future__ import annotations

import runpy
import streamlit as st

from ui_theme import apply_ui_theme
from ui_components import render_header, nav_to
from stats import aggregate_last_7_days, aggregate_last_7_days_by_mode, recent_attempts

import kanji
import talk

st.set_page_config(page_title="Hatena Basic", layout="centered")
apply_ui_theme()

st.session_state.setdefault("hub_view", "홈")
st.session_state.setdefault("user_plan", "free")  # "free" | "pro"

st.session_state.setdefault("daily_goal", 10)
def _plan():
    return str(st.session_state.get("user_plan","free")).lower()

def render_home():
    plan = _plan()
    render_header("왕초보 탈출 하테나일본어", user_plan=plan, show_home=False, show_mypage=True)

    st.markdown("<span id='ht_card_word' class='ht-cardbtn-anchor'></span>", unsafe_allow_html=True)
    if st.button("📘 단어 훈련", key="card_word"):
        nav_to("단어")
    st.markdown("<div style='margin-top:-10px;margin-bottom:14px;color:var(--subtext);font-size:0.92rem;'>단어 앱(기존 로직)으로 연결</div>", unsafe_allow_html=True)

    st.markdown("<span id='ht_card_kanji' class='ht-cardbtn-anchor'></span>", unsafe_allow_html=True)
    if st.button("🈶 한자 훈련", key="card_kanji"):
        nav_to("한자")
    st.markdown("<div style='margin-top:-10px;margin-bottom:14px;color:var(--subtext);font-size:0.92rem;'>한자 훈련</div>", unsafe_allow_html=True)

    st.markdown("<span id='ht_card_talk' class='ht-cardbtn-anchor'></span>", unsafe_allow_html=True)
    if st.button("💬 회화 훈련", key="card_talk"):
        nav_to("회화")
    st.markdown("<div style='margin-top:-10px;margin-bottom:14px;color:var(--subtext);font-size:0.92rem;'>말하기 1단계</div>", unsafe_allow_html=True)


def render_mypage_shell():
    plan = _plan()
    render_header("마이페이지", user_plan=plan, show_home=True, show_mypage=False)

    days, agg, streak, (today_total, today_correct), last_score = aggregate_last_7_days()
    score_txt = "-"
    if isinstance(last_score, (tuple, list)) and len(last_score)==2:
        score_txt = f"{int(last_score[0])}/{int(last_score[1])}"

    st.markdown("<div class='ht-mypage-wrap'>", unsafe_allow_html=True)

    st.markdown(f"""
        <div class="ht-kpi-row">
          <div class="ht-kpi">
            <div class="ht-kpi-label">연속 학습</div>
            <div class="ht-kpi-value">{streak}일</div>
            <div class="ht-kpi-sub">오늘도 루틴 유지!</div>
          </div>
          <div class="ht-kpi">
            <div class="ht-kpi-label">오늘 푼 문제</div>
            <div class="ht-kpi-value">{today_total}문</div>
            <div class="ht-kpi-sub">정답 {today_correct}문</div>
          </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="ht-kpi-row">
          <div class="ht-kpi">
            <div class="ht-kpi-label">최근 점수</div>
            <div class="ht-kpi-value">{score_txt}</div>
            <div class="ht-kpi-sub">최근 기록 기준</div>
          </div>
          <div class="ht-kpi">
            <div class="ht-kpi-label">오늘 날짜</div>
            <div class="ht-kpi-value">{__import__('datetime').date.today().strftime('%m/%d')}</div>
            <div class="ht-kpi-sub">10분만 해도 충분</div>
          </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='ht-divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='ht-section-title'>지난 7일 기록</div>", unsafe_allow_html=True)

    labels = ["월","화","수","목","금","토","일"]
    html = ["<div class='ht-heatmap'>"]
    for d in days:
        k = d.isoformat()
        total = agg[k]["total"]
        correct = agg[k]["correct"]
        rate = (correct/total) if total else 0
        w = int(rate*100)
        html.append(
            f"<div class='ht-heatcell'>"
            f"<div class='ht-heat-top'><span class='ht-heat-day'>{labels[d.weekday()]}</span>"
            f"<span class='ht-heat-date'>{d.strftime('%m/%d')}</span></div>"
            f"<div class='ht-heat-bar'><span style='width:{w}%'></span></div>"
            f"<div class='ht-heat-num'>{total}문 · 정답 {correct}</div>"
            f"</div>"
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    st.markdown("<div class='ht-divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='ht-section-title'>퀵 액션</div>", unsafe_allow_html=True)

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        if st.button("단어 훈련", type="primary", key="mp_go_word"):
            nav_to("단어")
    with r1c2:
        if st.button("한자 훈련", type="secondary", key="mp_go_kanji"):
            nav_to("한자")
    with r1c3:
        if st.button("회화 훈련", type="secondary", key="mp_go_talk"):
            nav_to("회화")

    pro_only = (plan != "pro")
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        if st.button("오답노트", type="secondary", key="mp_go_wrongs", disabled=pro_only):
            st.session_state["open_wrongs"] = True
            nav_to("단어")
    with r2c2:
        if st.button("다시풀기", type="secondary", key="mp_go_retry", disabled=pro_only):
            st.session_state["retry_mode"] = True
            nav_to("단어")
    with r2c3:
        if st.button("정복 초기화", type="secondary", key="mp_reset_master", disabled=pro_only):
            st.session_state["reset_mastered_request"] = True
            nav_to("단어")

    if pro_only:
        st.markdown("<div class='ht-cta'><div class='ht-cta-title'>PRO 기능</div><p class='ht-cta-sub'>오답노트/다시풀기/정복초기화는 PRO에서 사용 가능합니다.</p></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def run_word_app_embedded():
    # Embed: run hotena_basic.py but force embedded mode + sync hub actions
    st.session_state["_HATENA_EMBEDDED"] = True
    st.session_state["_hub_child"] = True
    st.session_state["hub_mode"] = True

    # ✅ MyPage quick actions -> hotena_basic
    if st.session_state.get("reset_mastered_request"):
        # let hotena_basic consume this once
        st.session_state["_hub_reset_mastery_once"] = True
        st.session_state["reset_mastered_request"] = False

    if st.session_state.get("retry_mode"):
        st.session_state["_hub_retry_wrongs_once"] = True
        st.session_state["retry_mode"] = False

    if st.session_state.get("open_wrongs"):
        # open word app's my page (오답 확인은 마이페이지에서)
        st.session_state["hub_view"] = "마이페이지"
        st.session_state["open_wrongs"] = False

    runpy.run_path("hotena_basic.py", run_name="__main__")

# ------------------------------------------------------------
# Router
# ------------------------------------------------------------
view = st.session_state.get("hub_view","홈")
plan = _plan()

if view == "홈":
    render_home()
elif view == "단어":
    # Word app has its own internal UI; we just embed it.
    run_word_app_embedded()
elif view == "한자":
    render_header("한자 훈련", user_plan=plan, show_home=True, show_mypage=True)
    kanji.render_kanji(user_plan=plan) if hasattr(kanji, "render_kanji") else st.write("kanji.py에 render_kanji가 필요합니다.")
elif view == "회화":
    render_header("회화 훈련", user_plan=plan, show_home=True, show_mypage=True)
    talk.render_talk(user_plan=plan)
elif view == "마이페이지":
    # show shell + also allow jumping into word app's my page if desired
    render_mypage_shell()
else:
    nav_to("홈")