from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

import core  # ✅ 중앙 효과음(SFX) 설정/재생

# ============================================================
# ✅ MyPage (Redesign v4 • Fix labels • CTA works • app+pos robust)
# - (1) "기타, Lv noun" 문제 해결:
#     - app/pos/level이 뒤섞인 레거시 데이터를 강하게 정규화
#     - 예: level='noun' → pos로 이동
#     - 예: app='noun'   → app='word', pos='noun'
#     - 예: app이 비었고 pos만 있으면 app='word'로 간주
# - (2) CTA 버튼 동작:
#     - Streamlit tabs는 programmatic select가 사실상 불가 → 탭 제거
#     - 상단 CTA 버튼 + 상단 "탭바(라디오)"로 뷰 전환(확실히 동작)
# - (3) 상단의 "PRO 이용중/관리자 메시지"는 mypage가 아니라 home.py(허브 공통 헤더)에서 나온 것
#     - 이 파일은 상단 메시지/뱃지를 출력하지 않음
# ============================================================

HATENA_BLUE = "#1E6BFF"

# ---------------------------
# Supabase helpers
# ---------------------------
def _sb() -> Any:
    sb = st.session_state.get("sb_authed") or st.session_state.get("sb")
    token = st.session_state.get("access_token")
    try:
        if sb and token and hasattr(sb, "postgrest") and hasattr(sb.postgrest, "auth"):
            sb.postgrest.auth(token)
    except Exception:
        pass
    return sb


# ---------------------------
# UI / CSS
# ---------------------------
def _inject_css() -> None:
    css = r"""<style>
:root {
  --ha-blue: __BLUE__;
  --ha-text: #0f172a;
  --ha-sub: #64748b;
  --ha-line: #e5e7eb;
  --ha-bg: #ffffff;
  --ha-chip: #f1f5f9;
  --ha-soft: rgba(30,107,255,0.08);
}

/* ============================================================
   ✅ TOP COMPACT + NO VERTICAL CENTER (MyPage only)
   - Streamlit 기본 상단 여백 제거
   - 혹시 적용된 세로 중앙정렬(flex center) 강제 해제
   ============================================================ */

header[data-testid="stHeader"]{ height:0px !important; min-height:0px !important; }
div[data-testid="stToolbar"]{ display:none !important; }
footer{ display:none !important; }

section.main > div.block-container{
  padding-top: 0rem !important;
  margin-top: 0rem !important;
  padding-bottom: 1.2rem !important;
}

/* 세로 가운데 정렬을 만드는 래퍼 강제 해제 */
div[data-testid="stAppViewContainer"] section.main,
div[data-testid="stAppViewContainer"] .main{
  justify-content: flex-start !important;
  align-items: stretch !important;
}

/* 일부 빌드에서 main이 flex+center로 잡히는 경우 */
div[data-testid="stAppViewContainer"] .main > div{
  justify-content: flex-start !important;
  align-items: stretch !important;
}

/* 첫 요소 상단 여백도 제거 */
div.block-container > div:first-child{
  margin-top: 0rem !important;
  padding-top: 0rem !important;
}

@media (max-width: 768px){
  section.main > div.block-container{
    padding-top: 0rem !important;
    margin-top: 0rem !important;
  }
}

.ha-wrap {
  font-family: Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  max-width: 980px;
  margin: 0 auto;
  padding: 2px 8px 18px 8px;
}

.ha-top {
  border: 1px solid var(--ha-line);
  border-radius: 18px;
  background: var(--ha-bg);
  padding: 14px 14px;
  margin: 2px 0 8px 0;
}



.ha-hero-pill{
  height:10px;
  border-radius:999px;
  background: rgba(0,0,0,0.07);
  overflow:hidden;
  border: 1px solid var(--ha-line);
  margin: 2px 0 12px 0;
}
.ha-hero-pill::after{
  content:"";
  display:block;
  height:100%;
  width:38%;
  background: rgba(30,107,255,0.22);
}

.ha-topbar {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
}

.ha-brand {
  display:flex;
  align-items:flex-start;
  gap: 10px;
}

.ha-logo {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(30,107,255,0.25);
  background: var(--ha-soft);
  display:flex;
  align-items:center;
  justify-content:center;
  color: var(--ha-blue);
  font-weight: 800;
}

.ha-title {
  font-size: 18px;
  font-weight: 800;
  color: var(--ha-text);
  letter-spacing: -0.3px;
  line-height: 1.15;
}
.ha-sub {
  margin-top: 3px;
  font-size: 12px;
  color: var(--ha-sub);
}

.ha-kpi {
  margin-top: 12px;
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.ha-kpi-item {
  border: 1px solid var(--ha-line);
  border-radius: 16px;
  padding: 12px 12px;
  background: #fff;
}
.ha-kpi-num {
  font-size: 26px;
  font-weight: 900;
  color: var(--ha-text);
  line-height: 1.0;
}
.ha-kpi-lbl {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ha-sub);
  font-weight: 800;
}

.ha-progress-row {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  margin-top: 10px;
}
.ha-progress {
  width: 100%;
  height: 10px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow:hidden;
  border: 1px solid var(--ha-line);
}
.ha-progress > div {
  height: 100%;
  background: var(--ha-blue);
  width: 0%;
}

.ha-chip {
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--ha-chip);
  border: 1px solid var(--ha-line);
  font-size: 12px;
  font-weight: 800;
  color: var(--ha-sub);
  white-space: nowrap;
}
.ha-chip b { color: var(--ha-text); }

.ha-badge {
  border: 1px solid rgba(30,107,255,0.25);
  background: rgba(30,107,255,0.08);
  color: var(--ha-blue);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.ha-row {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  flex-wrap: wrap;
}

/* ✅ messages: FORCE but keep existing box design */
.ha-card div[data-testid="stExpander"],
.ha-card div[data-testid="stExpander"] > details{
  border:0 !important;
  outline:0 !important;
  box-shadow:none !important;
  background:transparent !important;
  border-radius:0 !important;
  margin:0 !important;
  padding:0 !important;
}
.ha-card div[data-testid="stExpander"] summary{
  position:relative;
  margin:0 !important;
  padding:6px 2px 6px 30px !important; /* ✅ tighter list */
  border-bottom:1px solid var(--ha-line) !important;
  border-radius:0 !important;
  background:transparent !important;
  font-weight:900 !important;
  color:var(--ha-text) !important;
  letter-spacing:-0.2px !important;
}
/* ✅ ensure expanded container has inner bottom padding (prevents overlap with outer border) */
.ha-card div[data-testid="stExpander"] > details[open]{
  padding-bottom:14px !important;
  box-sizing:border-box !important;
}
.ha-card div[data-testid="stExpander"] summary:hover{background:#fbfbfd !important;}
.ha-card div[data-testid="stExpander"] summary svg{display:none !important;}
/* timeline line + dot */
.ha-card div[data-testid="stExpander"] summary:before{
  content:"";
  position:absolute;
  left:12px;
  top:0; bottom:0;
  width:2px;
  background:rgba(37,99,235,0.16);
  border-radius:99px;
}
.ha-card div[data-testid="stExpander"] summary:after{
  content:"";
  position:absolute;
  left:9px;
  top:50%;
  transform:translateY(-50%);
  width:10px; height:10px;
  border-radius:999px;
  background:#cbd5e1;
  border:2px solid #fff;
  box-shadow:0 0 0 2px rgba(37,99,235,0.10);
}
.ha-msg-unread .ha-card div[data-testid="stExpander"] summary:after{
  background:var(--ha-blue);
  box-shadow:0 0 0 2px rgba(37,99,235,0.18);
}
/* ✅ bigger white container ONLY (no design change) */
.ha-card div[data-testid="stExpander"] .streamlit-expanderContent{
  margin-top:8px !important;
  padding:14px 16px 30px 30px !important; /* ✅ extra bottom space so inner box doesn't touch outer border */
  border:0 !important;
  background:transparent !important;
}
/* ✅ reduce gap between list items */
.ha-card div[data-testid="stExpander"] + div[data-testid="stExpander"]{margin-top:2px !important;}
.ha-msg-bodyA{margin-top:8px; padding:0;}
.ha-msg-bodyA-inner{
  padding:12px 14px 16px 14px;
  background:#f8fafc;
  /* ✅ inner box: use accent + subtle outline (prevents "double bottom line" look) */
  border:0 !important;
  box-shadow: inset 0 0 0 1px var(--ha-line);
  border-left:4px solid var(--ha-blue);
  border-radius:12px;
  line-height:1.75;
  margin:10px 0 18px 0; /* ✅ create clear separation from outer card bottom line */
}


/* ✅ extra breathing room so expanded body never touches the outer (card) border */
.ha-card .ha-msg-scope{padding:0 0 16px 0;}
.ha-card .ha-msg-scope div[data-testid="stExpander"] .streamlit-expanderContent{
  padding:14px 14px 32px 14px !important; /* stronger */
}


/* ✅ force-kill expander outer box border */
.ha-msg-scope div[data-testid="stExpander"] > details{
  border:0 !important;
  outline:0 !important;
  box-shadow:none !important;
  background:transparent !important;
  border-radius:0 !important;
}
.ha-msg-scope div[data-testid="stExpander"] > details[open]{
  border:0 !important;
  outline:0 !important;
  box-shadow:none !important;
  background:transparent !important;
  border-radius:0 !important;
}
.ha-msg-scope div[data-testid="stExpander"]{
  border:0 !important;
  outline:0 !important;
  box-shadow:none !important;
  background:transparent !important;
  border-radius:0 !important;
}

.ha-msg-scope{margin-top:6px;}
/* remove expander outer box completely */
.ha-msg-scope div[data-testid="stExpander"]{
  border:0 !important;
  background:transparent !important;
  border-radius:0 !important;
  box-shadow:none !important;
}
.ha-msg-scope div[data-testid="stExpander"] details{
  border:0 !important;
  background:transparent !important;
  border-radius:0 !important;
  box-shadow:none !important;
}
.ha-msg-scope div[data-testid="stExpander"] summary{
  padding:10px 2px !important;
  border-bottom:1px solid var(--ha-line) !important;
  border-radius:0 !important;
  background:transparent !important;
  font-weight:900 !important;
  color:var(--ha-text) !important;
  letter-spacing:-0.2px !important;
}
.ha-msg-scope div[data-testid="stExpander"] summary:hover{
  background:#fbfbfd !important;
}
/* hide default chevron */
.ha-msg-scope div[data-testid="stExpander"] summary svg{
  display:none !important;
}
/* remove content card padding from streamlit */
.ha-msg-scope div[data-testid="stExpander"] .streamlit-expanderContent{
  padding:10px 12px 14px 30px !important;
  border:0 !important;
  background:transparent !important;
}
/* body: white + only left bar (no card-in-card) */
.ha-msg-bodyA{
  margin-top:14px;
  padding:0; /* spacing handled by expander content padding */
  background:transparent;
  border:0;
  border-radius:0;
  line-height:1.75;
}
.ha-msg-bodyA-inner{
  padding:10px 12px 14px 18px;
  background:#f8fafc;
  border:0;
  border-radius:12px;
  position:relative;
}


/* ✅ messages: inbox list style (A) */
.ha-msg-scope{margin-top:8px;}
.ha-msg-rowA{
  padding:10px 2px;
  border-bottom:1px solid var(--ha-line);
}
.ha-msg-rowA:last-child{border-bottom:0;}
.ha-msg-rowA:hover{background:#fbfbfd;}
.ha-msg-leftA{
  display:flex;
  align-items:center;
  gap:10px;
  min-width:0;
}
.ha-msg-titleA{
  font-weight:900;
  letter-spacing:-0.2px;
  color:var(--ha-text);
  font-size:15px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.ha-msg-dotA{
  width:8px; height:8px; border-radius:99px;
  background:var(--ha-blue);
  display:inline-block;
  flex:0 0 auto;
}
.ha-msg-rightA{
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap:wrap;
  justify-content:flex-end;
}
.ha-msg-chevronA{
  color:var(--ha-sub);
  font-size:14px;
  margin-left:2px;
}
.ha-msg-newA{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding:2px 8px;
  border-radius:999px;
  font-size:12px;
  font-weight:900;
  color:#fff;
  background: var(--ha-blue);
}
.ha-msg-bodyA{
  margin-top:8px;
  padding:10px 12px;
  background:#f8fafc;
  border:0;
  border-radius:12px;
  line-height:1.75;
  position:relative;
}
.ha-msg-bodyA:before{
  content:"";
  position:absolute;
  left:0; top:10px; bottom:10px;
  width:3px;
  background:rgba(37,99,235,0.55);
  border-radius:99px;
}
.ha-msg-bodyA-inner{padding-left:10px;}
/* title button chrome off (scoped) */
.ha-msg-titlebtnA [data-testid="stButton"] > button{
  width:100% !important;
  border:0 !important;
  background:transparent !important;
  padding:0 !important;
  margin:0 !important;
  box-shadow:none !important;
  text-align:left !important;
  font-weight:900 !important;
  letter-spacing:-0.2px !important;
  color:var(--ha-text) !important;
  font-size:15px !important;
}
.ha-msg-titlebtnA [data-testid="stButton"] > button:hover{
  background:transparent !important;
  color:var(--ha-blue) !important;
}


/* ✅ messages: minimal rows */
/* ✅ messages: row toggle (scoped) */
.ha-msg-scope [data-testid="stButton"] > button{
  width:100% !important;
  border:0 !important;
  background:transparent !important;
  padding:0 !important;
  margin:0 !important;
  box-shadow:none !important;
  text-align:left !important;
  font-weight:900 !important;
  color: var(--ha-text) !important;
  letter-spacing:-0.2px !important;
  font-size:15px !important;
}
.ha-msg-scope [data-testid="stButton"] > button:hover{
  background:transparent !important;
}
.ha-msg-row{
  border:0;
  border-radius:14px;
  background:#fff;
  padding:10px 12px;
  margin-top:10px;
}
.ha-msg-row:hover{background:#fbfbfd;}
.ha-msg-row-title{
  font-weight:900;
  color:var(--ha-text);
  letter-spacing:-0.2px;
  font-size:15px;
  display:flex;
  align-items:center;
  gap:8px;
}
.ha-msg-body{
  border:0;
  border-radius:14px;
  background:#f8fafc;
  padding:12px 12px;
  margin-top:8px;
  color:var(--ha-text);
  font-size:14px;
  line-height:1.75;
}

.ha-msg-card{
  border:0;
  border-radius:14px;
  background:#fff;
  padding:12px 14px;
  margin-top:10px;
}
.ha-msg-top{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:10px;
  flex-wrap:wrap;
}
.ha-msg-title{
  font-weight:900;
  color:var(--ha-text);
  letter-spacing:-0.2px;
  font-size:15px;
  display:flex;
  align-items:center;
  gap:8px;
}
.ha-msg-actions{display:flex; gap:8px; align-items:center; flex-wrap:wrap;}

.ha-inline {
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items:center;
}

.ha-section {
  border: 1px solid var(--ha-line);
  border-radius: 18px;
  padding: 12px 12px;
  background: var(--ha-bg);
  margin: 10px 0;
}

.ha-card {
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 10px 10px;
  background: #fff;
  margin: 8px 0;
}
.ha-card-title {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-weight: 900;
  color: var(--ha-text);
  letter-spacing: -0.2px;
}
.ha-meta {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ha-sub);
  display:flex;
  flex-wrap:wrap;
  gap: 8px;
}

.ha-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--ha-blue);
  display:inline-block;
  margin-right: 6px;
  opacity: 0.85;
}

/* mini calendar */
.ha-week {
  margin-top: 10px;
  border: 1px solid var(--ha-line);
  border-radius: 16px;
  padding: 10px 10px;
  background: #fff;
}
.ha-week-head {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.ha-week-title {
  font-size: 13px;
  font-weight: 900;
  color: var(--ha-text);
}
.ha-week-grid {
  display:grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}
.ha-day {
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 8px 6px;
  text-align:center;
  background: #fff;
}
.ha-day-top {
  font-size: 11px;
  color: var(--ha-sub);
  font-weight: 900;
}
.ha-day-num {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 900;
  color: var(--ha-text);
}
.ha-day-sub {
  margin-top: 2px;
  font-size: 11px;
  color: var(--ha-sub);
  font-weight: 800;
}

@media (max-width: 720px) {
  .ha-kpi { grid-template-columns: 1fr; }
  .ha-week-grid { gap: 6px; }
}

/* ✅ messages: clean minimal toggle row */
.ha-msg-scope{margin-top:8px;}
.ha-msg-row{
  border:0;
  border-radius:14px;
  background:#fff;
  padding:10px 12px;
  margin-top:10px;
}
.ha-msg-row:hover{background:#fbfbfd;}
.ha-msg-row.is-open{
  border-color: rgba(37,99,235,0.35);
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.ha-msg-click [data-testid="stButton"] > button{
  width:100%;
  border:0 !important;
  background:transparent !important;
  padding:0 !important;
  margin:0 !important;
  box-shadow:none !important;
  min-height:44px;
}
.ha-msg-click [data-testid="stButton"] > button:hover{background:transparent !important;}
.ha-msg-line{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
}
.ha-msg-left{
  display:flex;
  align-items:center;
  gap:8px;
  min-width:0;
}
.ha-msg-dot{
  width:8px; height:8px; border-radius:99px;
  background: var(--ha-blue);
  display:inline-block;
  transform: translateY(-1px);
}
.ha-msg-title{
  font-weight:900;
  letter-spacing:-0.2px;
  color:var(--ha-text);
  font-size:15px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.ha-msg-right{
  display:flex;
  align-items:center;
  gap:8px;
  flex-shrink:0;
  flex-wrap:wrap;
  justify-content:flex-end;
}
.ha-msg-new{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding:2px 8px;
  border-radius:999px;
  font-size:12px;
  font-weight:900;
  color:#fff;
  background: var(--ha-blue);
}
.ha-msg-chevron{
  color: var(--ha-sub);
  font-size:14px;
  margin-left:2px;
}
.ha-msg-body2{
  border:0;
  border-radius:14px;
  background:#f8fafc;
  padding:12px 12px;
  margin-top:8px;
  color:var(--ha-text);
  font-size:14px;
  line-height:1.75;
  position:relative;
}
.ha-msg-body2:before{
  content:"";
  position:absolute;
  left:0; top:10px; bottom:10px;
  width:3px;
  border-radius:99px;
  background: var(--ha-blue);
}
.ha-msg-body2-inner{ padding-left:10px; }


/* ============================================================
   ✅ 메시지 탭(ha-msg-card) 하단 겹침/라인 중복 방지 패치
   - 바깥 카드 하단선과 내부 박스 하단이 붙지 않게 여유 확보
   - Streamlit expander 기본 테두리/그림자 제거(강제)
   ============================================================ */
.ha-msg-card{
  padding-bottom: 18px !important;
}

/* expander 전체 외곽선/그림자 완전 제거 */
.ha-msg-card div[data-testid="stExpander"],
.ha-msg-card div[data-testid="stExpander"] > div,
.ha-msg-card div[data-testid="stExpander"] details,
.ha-msg-card div[data-testid="stExpander"] details > summary,
.ha-msg-card div[data-testid="stExpander"] .streamlit-expanderContent{
  border: 0 !important;
  box-shadow: none !important;
  outline: 0 !important;
  background: transparent !important;
}

/* 펼친 영역은 아래 여백을 넉넉히(내부 박스가 카드 하단선에 닿지 않게) */
.ha-msg-card div[data-testid="stExpander"] .streamlit-expanderContent{
  padding: 14px 14px 34px 14px !important;
}


/* ============================================================
   ✅ v4_9_10 overrides (message tab polish)
   - inner box background removed
   - inner left line lighter
   - outer padding tightened
   ============================================================ */
.ha-msg-bodyA-inner{
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
}

.ha-msg-bodyA{
  background: transparent !important;
  padding: 0 !important;
  margin-top: 8px !important;
}

/* left accent line (lighter) */
.ha-msg-bodyA:before{
  background: rgba(37,99,235,0.20) !important;
  width: 3px !important;
}

/* tighten outer spacing so it doesn't feel too tall */
.ha-card div[data-testid="stExpander"] > details[open]{
  padding-bottom: 4px !important;
}
.ha-card div[data-testid="stExpander"] .streamlit-expanderContent{
  padding: 8px 10px 12px 26px !important;
}
.ha-card .ha-msg-scope div[data-testid="stExpander"] .streamlit-expanderContent{
  padding: 8px 10px 12px 12px !important;
}

/* reduce extra margin that can make bottom feel double-lined */
.ha-msg-bodyA-inner{
  margin: 6px 0 8px 0 !important;
  padding: 8px 10px 10px 16px !important;
  border-radius: 12px !important;
}



/* ============================================================
   ✅ V4.9.12 HOTFIX: message list spacing tighter
   - Streamlit wraps expanders in element-container with default margins.
   - Force near-zero spacing only inside message scope.
   ============================================================ */
.ha-msg-scope div[data-testid="element-container"]{
  margin: 0 !important;
  padding: 0 !important;
}
.ha-msg-scope div[data-testid="stVerticalBlock"]{
  gap: 0 !important;
}
.ha-msg-scope div[data-testid="stExpander"]{
  margin: 0 !important;
}
.ha-msg-scope div[data-testid="stExpander"] + div[data-testid="stExpander"]{
  margin-top: 0px !important; /* almost 붙이기 */
}

/* Optional: a hairline separation without big gap */
.ha-msg-scope div[data-testid="stExpander"] summary{
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}


/* ============================================================
   ✅ V4.9.15: 메시지 목록 '붙이기' 최종
   - Streamlit wrapper 기본 여백 완전 제거
   - Expander 사이 간격 0px (완전 밀착)
   - 보더 겹침 방지(윗선 투명)
   ============================================================ */

.ha-msg-scope div[data-testid="stVerticalBlock"] > div,
.ha-msg-scope div[data-testid="stVerticalBlock"] > div > div,
.ha-msg-scope div[data-testid="stElementContainer"],
.ha-msg-scope div[data-testid="element-container"],
.ha-msg-scope .element-container{
  margin: 0 !important;
  padding: 0 !important;
}
.ha-msg-scope div[data-testid="stVerticalBlock"]{ gap: 0 !important; }

.ha-msg-scope div[data-testid="stExpander"]{
  margin: 0 !important;
}

/* ✅ 완전 밀착 */
.ha-msg-scope div[data-testid="stExpander"] + div[data-testid="stExpander"]{
  margin-top: 0 !important;
}

/* summary(닫힌 상태 박스)도 여백 최소 */
.ha-msg-scope div[data-testid="stExpander"] summary{
  margin: 0 !important;
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}

/* 보더가 두 줄처럼 보이면: 위 카드의 아래선만 남기기 */
.ha-msg-scope div[data-testid="stExpander"] + div[data-testid="stExpander"] summary{
  border-top-color: transparent !important;
}

/* ============================================================
   ✅ 메시지 목록 '붙게' (간격 원인: element-container / markdown wrapper)
   - 다른 탭 영향 없도록 .ha-msg-scope 내부만
   ============================================================ */

/* Streamlit wrapper 여백/간격 제거 */
.ha-msg-scope div[data-testid="stVerticalBlock"]{
  gap: 0 !important;
}
.ha-msg-scope .element-container,
.ha-msg-scope div[data-testid="stElementContainer"]{
  margin: 0 !important;
  padding: 0 !important;
}

/* markdown 블록이 만드는 빈 줄/여백 제거 */
.ha-msg-scope div[data-testid="stMarkdownContainer"],
.ha-msg-scope .stMarkdown,
.ha-msg-scope .stMarkdown > div{
  margin: 0 !important;
  padding: 0 !important;
}
.ha-msg-scope p, 
.ha-msg-scope ul, 
.ha-msg-scope ol{
  margin: 0 !important;
}

/* expander 행간: 완전 밀착(필요시 2px로) */
.ha-msg-scope div[data-testid="stExpander"] + div[data-testid="stExpander"]{
  margin-top: 0px !important;
}


/* ============================================================
   ✅ 10분 컷: 메시지 목록 UI 업그레이드 (간격은 그대로 유지)
   - summary를 '리스트 카드'처럼 보이게
   - hover/active 반응
   - open 상태에서 content와 자연스럽게 연결
   ============================================================ */

.ha-msg-scope div[data-testid="stExpander"]{
  margin: 0 !important;
}

/* 리스트 행(닫힌 상태) */
.ha-msg-scope div[data-testid="stExpander"] summary{
  margin: 0 !important;
  padding: 10px 12px !important;
  border: 1px solid var(--ha-line) !important;
  border-radius: 14px !important;
  background: #fff !important;
  box-shadow: none !important;
  transition: transform 120ms ease, box-shadow 120ms ease;
}

/* hover */
.ha-msg-scope div[data-testid="stExpander"] summary:hover{
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06) !important;
}

/* open일 때: summary와 본문을 하나의 카드처럼 연결 */
.ha-msg-scope div[data-testid="stExpander"] > details[open] > summary{
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  border-bottom: 0 !important;
  box-shadow: none !important;
}

/* 펼친 본문 */
.ha-msg-scope div[data-testid="stExpander"] .streamlit-expanderContent{
  margin: 0 !important;
  padding: 10px 12px 12px 12px !important;
  border: 1px solid var(--ha-line) !important;
  border-top: 0 !important;
  border-bottom-left-radius: 14px !important;
  border-bottom-right-radius: 14px !important;
  background: #fff !important;
}

/* expander 행간: 완전 밀착 유지(원하면 2px로) */
.ha-msg-scope div[data-testid="stExpander"] + div[data-testid="stExpander"]{
  margin-top: 2px !important;
}


/* Prevent top action buttons from wrapping */
div.stButton > button { white-space: nowrap !important; }
</style>"""
    css = css.replace("__BLUE__", str(HATENA_BLUE))
    st.markdown(css, unsafe_allow_html=True)

def _wrap_start() -> None:
    st.markdown('<div class="ha-wrap">', unsafe_allow_html=True)


def _wrap_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)



# ---------------------------
# Card renderer (iframe) to prevent HTML tags being shown as text
# ---------------------------
def _escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _card_iframe_html(title: str, meta_html: str, body_html: str = "") -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"/>
<style>
:root {{
  --ha-blue: {HATENA_BLUE};
  --ha-text: #0f172a;
  --ha-sub: #64748b;
  --ha-line: #e5e7eb;
  --ha-chip: #f1f5f9;
  --ha-soft: rgba(30,107,255,0.08);
}}
body {{ margin:0; font-family: Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}
.card {{
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 10px 10px;
  background: #fff;
  box-sizing: border-box;
}}
.title {{
  font-weight: 900;
  color: var(--ha-text);
  letter-spacing: -0.2px;
  font-size: 16px;
}}
.meta {{
  margin-top: 6px;
  font-size: 12px;
  color: var(--ha-sub);
  display:flex;
  flex-wrap:wrap;
  gap: 8px;
}}
.chip {{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--ha-chip);
  border: 1px solid var(--ha-line);
  font-size: 12px;
  font-weight: 800;
  color: var(--ha-sub);
  white-space: nowrap;
}}
.chip b {{ color: var(--ha-text); }}
.badge {{
  border: 1px solid rgba(30,107,255,0.25);
  background: rgba(30,107,255,0.08);
  color: var(--ha-blue);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}}
.body {{
  margin-top: 8px;
  color: var(--ha-text);
  font-size: 14px;
  line-height: 1.55;
}}
</style></head>
<body>
  <div class="card">
    <div class="title">{_escape_html(title)}</div>
    <div class="meta">{meta_html}</div>
    {('<div class="body">'+body_html+'</div>') if body_html else ''}
  </div>
</body></html>"""
# ---------------------------
# Data loaders (RLS-safe)
# ---------------------------
def _safe_select(table: str, cols: str = "*", limit: int = 200, order: Optional[str] = None, desc: bool = True) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        q = sb.table(table).select(cols)
        if order:
            q = q.order(order, desc=desc)
        if limit:
            q = q.limit(limit)
        res = q.execute()
        data = getattr(res, "data", None)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_wrongs(limit: int = 400) -> Tuple[List[Dict[str, Any]], str]:
    """오답(wrong_notes) 로드.

    ✅ 규칙(고정):
    - 테이블은 반드시 wrong_notes만 사용합니다.
    - 단, 스키마/컬럼 차이로 select(cols=...)가 실패하는 환경을 대비해
      1) 지정 컬럼 조회 → 2) '*' 전체 조회로 1회 fallback 합니다.
    """
    table = "wrong_notes"

    # 1차: 우리가 기대하는 대표 컬럼 세트
    cols1 = "id, user_id, app, pos, level, jp_word, word, term, reading, yomi, kana, meaning, meaning_kr, kr_meaning, correct_answer, correct, user_answer, answer, created_at"
    rows = _safe_select(table, cols=cols1, limit=limit, order="created_at", desc=True)

    # 2차: 컬럼 미존재/스키마 차이로 실패(=빈 배열 반환)하는 경우 전체 조회로 재시도
    if not rows:
        rows = _safe_select(table, cols="*", limit=limit, order="created_at", desc=True)

    if rows:
        # normalize: 다양한 스키마를 mypage가 쓰는 키로 최대한 흡수
        for r in rows:
            # jp_word / word / term / jp / question
            if not r.get("jp_word"):
                r["jp_word"] = r.get("word") or r.get("term") or r.get("jp") or r.get("question") or r.get("prompt")
            # reading
            if not r.get("reading"):
                r["reading"] = r.get("yomi") or r.get("kana") or r.get("furigana") or r.get("pron") or r.get("pronunciation")
            # meaning
            if not r.get("meaning"):
                r["meaning"] = r.get("meaning_kr") or r.get("kr_meaning") or r.get("ko_meaning") or r.get("meaning_jp")
            # correct / user_answer
            if "correct_answer" not in r or r.get("correct_answer") in (None, ""):
                r["correct_answer"] = r.get("correct_answer") or r.get("correct") or r.get("gold") or r.get("target")
            if "user_answer" not in r or r.get("user_answer") in (None, ""):
                r["user_answer"] = r.get("user_answer") or r.get("answer") or r.get("pred") or r.get("user")

        return rows, table

    return [], table



def _load_messages(limit: int = 300) -> List[Dict[str, Any]]:
    cols = "id, user_id, title, body, created_at, read_at"
    return _safe_select("user_messages", cols=cols, limit=limit, order="created_at", desc=True)


def _load_attempts(limit: int = 500) -> Tuple[List[Dict[str, Any]], str]:
    sb = _sb()
    if not sb:
        return [], "no-sb"
    candidates = [
        "id, user_id, app, pos, level, total, correct, wrong, score, created_at",
        "id, user_id, app, pos, level, quiz_len, correct_cnt, wrong_cnt, score, created_at",
        "id, user_id, app, pos, level, total_questions, correct_answers, wrong_answers, score, created_at",
        "*",
    ]
    last_err = "unknown"
    for cols in candidates:
        try:
            q = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(limit)
            res = q.execute()
            data = getattr(res, "data", None)
            if isinstance(data, list):
                return data, "ok"
        except Exception as e:
            last_err = str(e)
            continue
    return [], last_err


# ---------------------------
# Normalization (핵심)
# ---------------------------
_POS_KEYS = {
    "noun", "n", "명사",
    "verb", "v", "동사",
    "adj", "adjective", "형용사",
    "adv", "adverb", "부사",
    "particle", "조사",
    "conj", "conjunction", "접속사",
}
_APP_KEYS_WORD = {"word", "words", "vocab"}
_APP_KEYS_KANJI = {"kanji", "hanja"}
_APP_KEYS_TALK = {"talk", "conversation", "speech"}

def _looks_like_pos(x: Any) -> bool:
    s = str(x or "").strip().lower()
    return s in _POS_KEYS

def _looks_like_app(x: Any) -> bool:
    s = str(x or "").strip().lower()
    return s in (_APP_KEYS_WORD | _APP_KEYS_KANJI | _APP_KEYS_TALK)

def _normalize_attempt(a: Dict[str, Any]) -> Dict[str, Any]:
    """
    현재 문제:
      - app='기타'로 떨어짐
      - level='noun' 같은 값이 들어와서 "Lv noun" 노출
    해결:
      - app/pos/level이 뒤섞인 레거시 값을 최대한 복구
    """
    a = dict(a)

    app = (a.get("app") or "").strip()
    pos = (a.get("pos") or "").strip()
    level = (a.get("level") or "").strip()

    app_l = app.lower()
    pos_l = pos.lower()
    level_l = level.lower()

    # 1) app에 pos가 들어간 경우: app='noun'
    if _looks_like_pos(app) and not pos:
        a["pos"] = app
        a["app"] = "word"
        app, pos, level = "word", a["pos"], level

    # 2) level에 pos가 들어간 경우: level='noun'
    if _looks_like_pos(level) and not pos:
        a["pos"] = level
        a["level"] = ""  # 레벨이 없으면 공란으로
        pos, level = a["pos"], ""

    # 3) app이 비었는데 pos만 있는 경우: 단어앱으로 간주
    if not app and pos:
        a["app"] = "word"
        app = "word"

    # 4) app이 알 수 없는 값인데 pos가 있다면 → 단어로 간주(레거시)
    if app and (not _looks_like_app(app)) and pos:
        a["app"] = "word"
        app = "word"

    # 5) level에 app이 들어간 경우(실수): level='kanji'
    if _looks_like_app(level) and not app:
        a["app"] = level
        a["level"] = ""
        app, level = a["app"], ""

    return a


# ---------------------------
# Formatting
# ---------------------------
def _fmt_dt(s: Any) -> str:
    if not s:
        return "-"
    try:
        if isinstance(s, str):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif isinstance(s, datetime):
            dt = s
        else:
            return str(s)
        return dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)


def _app_label(app: Optional[str]) -> str:
    a = (app or "").lower().strip()
    if a in _APP_KEYS_WORD:
        return "단어"
    if a in _APP_KEYS_KANJI:
        return "한자"
    if a in _APP_KEYS_TALK:
        return "회화"
    return "단어"  # 안전: 기록은 기본 단어로 표시(‘기타’ 최소화)




def _wrong_app_label(w: dict) -> str:
    """Map a wrong_note row to one of: 단어/한자/회화.
    Priority: quiz_type -> app -> default(단어).
    This must be available before any UI renders (used in top summary/week widgets).
    """
    try:
        qt = (w.get("quiz_type") or w.get("type") or w.get("quiz") or "").lower().strip()
        ap = (w.get("app") or "").lower().strip()

        if qt in ("word", "vocab", "vocabulary"):
            return "단어"
        if qt in ("kanji", "hanja"):
            return "한자"
        if qt in ("talk", "conversation", "speech", "speaking"):
            return "회화"

        return _app_label(ap) or "단어"
    except Exception:
        return "단어"


def _pos_label(pos: Optional[str]) -> Optional[str]:
    p = (pos or "").strip()
    if not p:
        return None
    pl = p.lower()
    if pl in ("noun", "n"):
        return "명사"
    if pl in ("verb", "v"):
        return "동사"
    if pl in ("adj", "adjective"):
        return "형용사"
    if pl in ("adv", "adverb"):
        return "부사"
    if pl == "particle":
        return "조사"
    if pl in ("conj", "conjunction"):
        return "접속사"
    if p in ("명사", "동사", "형용사", "부사", "조사", "접속사"):
        return p
    return p


def _num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return "0"



# ---------------------------
# Wrong quiz (simple 4-choice)
# ---------------------------
def _make_wrong_quiz(wrongs: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    import random
    pool = [w for w in wrongs if (w.get("jp_word") and (w.get("meaning") or w.get("correct_answer")))]
    random.shuffle(pool)
    pool = pool[: max(n, 20)]
    meanings = list({((w.get("meaning") or w.get("correct_answer") or "")).strip() for w in pool if ((w.get("meaning") or w.get("correct_answer") or "")).strip()})
    quiz = []
    for w in pool[:n]:
        correct = (w.get("meaning") or w.get("correct_answer") or "").strip()
        opts = [correct]
        others = [m for m in meanings if m != correct]
        random.shuffle(others)
        opts += others[:3]
        # ensure 4 unique
        opts = list(dict.fromkeys([o for o in opts if o]))
        while len(opts) < 4 and others:
            cand = others.pop()
            if cand and cand not in opts:
                opts.append(cand)
        random.shuffle(opts)
        quiz.append({
            "jp_word": w.get("jp_word"),
            "reading": w.get("reading"),
            "correct": correct,
            "options": opts[:4],
        })
    return quiz

def _build_wrong_quiz_for_app(app_label: str, wrongs_for_quiz: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    """Build quiz items for the selected app using each module's own pool, when available.

    - 단어: hotena_basic.build_quiz_from_wrongs
    - 한자: app.build_quiz_from_wrongs
    - 회화: mypage의 간단 퀴즈(_make_wrong_quiz) fallback
    """
    import random, importlib

    app_label = str(app_label or "").strip()

    # 공통: wrongs -> [{"단어": jp_word}] 형태로 변환 (각 모듈이 기대)
    def _to_wrong_list(ws: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        out = []
        for w in (ws or []):
            jp = (w.get("jp_word") or w.get("question") or "").strip()
            if jp:
                out.append({"단어": jp})
        # 중복 제거(순서 유지)
        seen = set()
        uniq = []
        for d in out:
            k = d.get("단어", "")
            if k and (k not in seen):
                seen.add(k)
                uniq.append(d)
        return uniq

    # ✅ 단어/한자는 각 모듈의 build_quiz_from_wrongs를 우선 사용
    if app_label in ("단어", "한자"):
        mod_name = "hotena_basic" if app_label == "단어" else "app"
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, "build_quiz_from_wrongs", None)
            if callable(fn):
                qtype = "meaning"  # 마이페이지 오답시험은 '뜻' 방식으로 통일
                quiz_all = fn(_to_wrong_list(wrongs_for_quiz), qtype)
                if isinstance(quiz_all, list) and quiz_all:
                    random.shuffle(quiz_all)
                    return quiz_all[: int(n)]
        except Exception:
            # 모듈/풀 초기화 문제 등은 fallback
            pass

    # ✅ fallback: mypage의 간단 퀴즈(뜻 기반 4지선다)
    return _make_wrong_quiz(wrongs_for_quiz, n=int(n))

def _calc_score(a: Dict[str, Any]) -> Optional[float]:
    score = a.get("score")
    if score is not None:
        try:
            return float(score)
        except Exception:
            return None
    total = a.get("total") or a.get("quiz_len") or a.get("total_questions")
    correct = a.get("correct") or a.get("correct_cnt") or a.get("correct_answers")
    try:
        if total and correct is not None:
            return round((float(correct) / float(total)) * 100, 1)
    except Exception:
        pass
    return None


def _calc_total_wrong(a: Dict[str, Any]) -> Tuple[Any, Any]:
    total = a.get("total") or a.get("quiz_len") or a.get("total_questions") or "-"
    wrong = a.get("wrong") or a.get("wrong_cnt") or a.get("wrong_answers") or "-"
    return total, wrong


def _to_dt_kst(any_dt: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(any_dt).replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=9)))
    except Exception:
        return None


# ---------------------------
# Navigation
# ---------------------------
def _go_home() -> None:
    # ✅ home.py router uses query param "p" to set st.session_state["hub_page"].
    # If URL still has ?p=my, it can override hub_page on rerun.
    # So we update BOTH: session_state + query param.
    try:
        st.query_params["p"] = "home"
    except Exception:
        try:
            st.experimental_set_query_params(p="home")
        except Exception:
            pass

    st.session_state["hub_page"] = "home"
    # optional compatibility keys (older builds)
    st.session_state["page"] = "home"
    st.session_state["current_page"] = "home"

    st.rerun()


def _logout() -> None:
    """Best-effort logout (MyPage only).

    Why: home.py may restore auth from persisted storage on rerun.
    So we clear session_state tokens + (if present) cookie/localStorage + URL params,
    then force a hard reload to a clean URL.
    """
    sb = _sb()

    # 1) Supabase sign out (server-side)
    try:
        if sb and hasattr(sb, "auth") and hasattr(sb.auth, "sign_out"):
            sb.auth.sign_out()
    except Exception:
        pass

    # 2) Clear common auth/session keys
    explicit_keys = [
        "access_token", "refresh_token", "user_id", "uid", "email",
        "sb_authed", "sb",
        "is_admin", "plan", "user_plan", "pro_until",
        "cookies",  # if a cookie-manager is stored here, we handle below as well
    ]
    for k in explicit_keys:
        if k in st.session_state:
            st.session_state[k] = None

    # 3) Also clear any key that smells like auth/session (safe, but focused)
    for k in list(st.session_state.keys()):
        lk = str(k).lower()
        if any(s in lk for s in ("token", "refresh", "access", "auth", "supabase", "jwt", "user", "profile")):
            try:
                st.session_state[k] = None
            except Exception:
                pass

    # 4) Try to clear cookies if a cookie manager exists
    try:
        cm = st.session_state.get("cookies")
        # common APIs: .delete(key) / .remove(key) / dict-like pop
        for ck in ("access_token", "refresh_token", "sb_access_token", "sb_refresh_token"):
            try:
                if hasattr(cm, "delete"):
                    cm.delete(ck)
                elif hasattr(cm, "remove"):
                    cm.remove(ck)
                elif isinstance(cm, dict):
                    cm.pop(ck, None)
            except Exception:
                pass
        # some managers need save()
        try:
            if hasattr(cm, "save"):
                cm.save()
        except Exception:
            pass
    except Exception:
        pass

    # 5) Ensure router goes home AND strip query params (so ?p=my doesn't pull you back)
    try:
        st.query_params.clear()
        st.query_params["p"] = "home"
    except Exception:
        try:
            st.experimental_set_query_params(p="home")
        except Exception:
            pass

    for key in ("hub_page", "page", "current_page"):
        if key in st.session_state:
            st.session_state[key] = "home"

    # 6) Hard reload + browser storage cleanup (best effort)
    try:
        components.html(
            """
            <script>
              try { localStorage.clear(); } catch(e) {}
              try { sessionStorage.clear(); } catch(e) {}
              try {
                const url = new URL(window.location.href);
                url.search = '';
                url.hash = '';
                // keep only p=home to align with hub router
                url.searchParams.set('p','home');
                window.location.replace(url.toString());
              } catch(e) {
                window.location.reload();
              }
            </script>
            """,
            height=0,
        )
    except Exception:
        pass

    st.rerun()
# ---------------------------
# Mini widget
# ---------------------------
def _week_counts_by_app(attempts: List[Dict[str, Any]]) -> Tuple[List[datetime], Dict[str, List[int]]]:
    """최근 7일 학습 횟수를 앱(단어/한자/회화)별로 집계."""
    now = datetime.now(timezone(timedelta(hours=9)))
    days = [(now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0) for i in range(6, -1, -1)]
    counts = {"단어": [0]*7, "한자": [0]*7, "회화": [0]*7}

    for a0 in attempts:
        a = _normalize_attempt(a0)
        dt = _to_dt_kst(a.get("created_at"))
        if not dt:
            continue
        d0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        app_name = _app_label(a.get("app"))
        if app_name not in counts:
            # 안전: 레거시는 단어로 처리
            app_name = "단어"
        for i, day in enumerate(days):
            if d0 == day:
                counts[app_name][i] += 1
                break

    return days, counts


def _render_week_widget(attempts: List[Dict[str, Any]]) -> None:
    days, by_app = _week_counts_by_app(attempts)

    # day total + max for heat
    totals = [by_app["단어"][i] + by_app["한자"][i] + by_app["회화"][i] for i in range(7)]
    mx = max(totals) if totals else 0
    dow_kr = ["월", "화", "수", "목", "금", "토", "일"]

    blocks = []
    for idx, day in enumerate(days):
        wd = dow_kr[day.weekday()]
        t = totals[idx]
        w = by_app["단어"][idx]
        k = by_app["한자"][idx]
        c = by_app["회화"][idx]

        if mx <= 0:
            bg = "rgba(30,107,255,0.06)"
            bd = "rgba(229,231,235,1)"
        else:
            alpha = 0.08 + (0.20 * (t / mx)) if t > 0 else 0.06
            bg = f"rgba(30,107,255,{alpha:.3f})"
            bd = "rgba(30,107,255,0.22)" if t > 0 else "rgba(229,231,235,1)"

        # ✅ 앱별 표기(한눈에): 단어/한자/회화
        sub = f"{t}회"
        sub2 = f"""<div>단어 {w}</div><div>한자 {k}</div><div>회화 {c}</div>"""

        blocks.append(
            f"""
<div class="ha-day" style="background:{bg}; border-color:{bd};">
  <div class="ha-day-top">{wd}</div>
  <div class="ha-day-num">{day.day}</div>
  <div class="ha-day-sub">{sub}</div>
  <div class="ha-day-sub" style="margin-top:4px; font-size:10px; line-height:1.25;">
    {sub2}
  </div>
</div>
"""
        )

    total = sum(totals)
    streak = 0
    for t in reversed(totals):
        if t > 0:
            streak += 1
        else:
            break

    # header chips: total + per-app
    total_word = sum(by_app["단어"])
    total_kanji = sum(by_app["한자"])
    total_talk = sum(by_app["회화"])

    st.markdown(
        f"""
<div class="ha-week">
  <div class="ha-week-head">
    <div class="ha-week-title">최근 7일 학습</div>
    <div class="ha-inline">
      <span class="ha-chip">총 <b>{total}</b>회</span>
      <span class="ha-chip">단어 <b>{total_word}</b></span>
      <span class="ha-chip">한자 <b>{total_kanji}</b></span>
      <span class="ha-chip">회화 <b>{total_talk}</b></span>
      <span class="ha-chip">연속 <b>{streak}</b>일</span>
    </div>
  </div>
  <div class="ha-week-grid">
    {''.join(blocks)}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_filter_chips(title: str, key: str) -> List[str]:
    options = ["단어", "한자", "회화"]
    selected = st.multiselect(title, options=options, default=st.session_state.get(key, []), key=key)
    if selected:
        chips = " ".join([f'<span class="ha-badge">{s}</span>' for s in selected])
        st.markdown(f'<div class="ha-inline" style="margin-top:6px;">{chips}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ha-inline" style="margin-top:6px;"><span class="ha-chip">전체</span></div>', unsafe_allow_html=True)
    return selected


# ---------------------------
# Top summary (NO messages duplication)
# ---------------------------
def _render_top_summary(wrongs: List[Dict[str, Any]], attempts: List[Dict[str, Any]]) -> None:
    wrong_total = len(wrongs)

    scores = []
    for a in attempts:
        sc = _calc_score(a)
        if sc is not None:
            scores.append(sc)
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    now = datetime.now(timezone(timedelta(hours=9)))
    week_ago = now - timedelta(days=7)
    recent_cnt = 0
    for a in attempts:
        dt = _to_dt_kst(a.get("created_at"))
        if dt and dt >= week_ago:
            recent_cnt += 1

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cnt = 0
    for a in attempts:
        dt = _to_dt_kst(a.get("created_at"))
        if dt and dt >= month_start:
            month_cnt += 1

    goal = st.session_state.get("goal_sets") or st.session_state.get("hub_goal_sets") or 20
    try:
        goal = max(1, int(goal))
    except Exception:
        goal = 20
    pct = min(100, round((month_cnt / goal) * 100, 0)) if goal else 0

    st.markdown('<div class="ha-top">', unsafe_allow_html=True)
    st.markdown('<div class="ha-hero-pill"></div>', unsafe_allow_html=True)

    st.markdown(
        """
<div class="ha-topbar">
  <div class="ha-brand">
    <div class="ha-logo">は</div>
    <div>
      <div class="ha-title">하테나일본어 · 마이페이지</div>
      <div class="ha-sub">핵심은 위에, 상세는 아래에서 빠르게 확인하세요.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


    # ✅ 상단 액션바: (좌) 소리 토글  (우) 홈/로그아웃 — 한 줄 정렬(PC/모바일)
    actL, actR = st.columns([5.2, 4.8], vertical_alignment="center")
    with actL:
        cT, cLbl = st.columns([1.2, 8.8], gap="small", vertical_alignment="center")
        with cT:
            _cur_sfx = bool(core.is_sfx_enabled(True))
            _new_sfx = st.toggle("🔊", value=_cur_sfx, key="myp_sfx_toggle", label_visibility="collapsed")
            core.set_sfx_enabled(bool(_new_sfx))
        with cLbl:
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:10px; white-space:nowrap;'>"
                f"<span style='font-weight:800;'>🔊 소리</span>"
                f"<span style='font-size:0.95rem; opacity:0.75; font-weight:800;'>{'ON' if _new_sfx else 'OFF'}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with actR:
        # 오른쪽 정렬(스페이서 + 버튼 2개)
        sp, b1, b2 = st.columns([3.8, 2.7, 3.5], gap="small", vertical_alignment="center")
        with sp:
            st.markdown("<div></div>", unsafe_allow_html=True)
        with b1:
            if st.button("🏠 홈", key="myp_v4_home", use_container_width=False):
                _go_home()
        with b2:
            if st.button("🚪 로그아웃", key="myp_v4_logout", use_container_width=True):
                _logout()

    st.markdown(

        f"""
<div class="ha-row">
  <div class="ha-inline">
    <span class="ha-chip"><b>이번 달</b> {month_cnt}/{goal}회</span>
    <span class="ha-chip"><b>{int(pct)}%</b> 진행</span>
  </div>
</div>
<div class="ha-progress-row">
  <div class="ha-progress"><div style="width:{pct}%;"></div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ============================================================
    # ✅ 추가 리포트(3장) + 추천 1줄(+TOP10)
    # ============================================================
    # 연속 학습일(스트릭)
    def _calc_streak(atts: List[Dict[str, Any]]) -> int:
        days = set()
        for a in (atts or []):
            d = _to_dt_kst(a.get("created_at"))
            if d:
                days.add(d.date())
        if not days:
            return 0
        today = datetime.now(timezone(timedelta(hours=9))).date()
        streak = 0
        cur = today
        while cur in days:
            streak += 1
            cur = cur - timedelta(days=1)
        return streak

    streak = _calc_streak(attempts)

    # 이번 주 총 풀이수(앱별)
    def _app_key_from_attempt(a: Dict[str, Any]) -> str:
        ap = (a.get("app") or a.get("quiz_type") or a.get("type") or "").lower().strip()
        if ap in ("word", "vocab", "vocabulary"):
            return "단어"
        if ap in ("kanji", "hanja"):
            return "한자"
        if ap in ("talk", "conversation", "speech", "speaking"):
            return "회화"
        return _app_label(ap) or "단어"

    week_start = (datetime.now(timezone(timedelta(hours=9))) - timedelta(days=6)).date()
    wk = {"단어": 0, "한자": 0, "회화": 0}
    for a in attempts:
        d = _to_dt_kst(a.get("created_at"))
        if d and d.date() >= week_start:
            k = _app_key_from_attempt(a)
            if k in wk:
                wk[k] += 1
    week_total = sum(wk.values())

    # 가장 많이 틀린 유형(오답 기반)
    wc = {"단어": 0, "한자": 0, "회화": 0}
    for w in (wrongs or []):
        lb = _wrong_app_label(w)
        if lb in wc:
            wc[lb] += 1
    top_wrong = max(wc.items(), key=lambda x: x[1])[0] if any(wc.values()) else "-"

    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='ha-kpi-item'><div class='ha-kpi-num'>{_num(streak)}</div><div class='ha-kpi-lbl'>연속 학습일</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='ha-kpi-item'><div class='ha-kpi-num'>{_num(week_total)}</div><div class='ha-kpi-lbl'>이번 주 풀이수</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='ha-kpi-item'><div class='ha-kpi-num'>{top_wrong}</div><div class='ha-kpi-lbl'>최다 오답 유형</div></div>", unsafe_allow_html=True)
    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)


    st.markdown(
        f"""
<div class="ha-kpi">
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{_num(wrong_total)}</div>
    <div class="ha-kpi-lbl">오답</div>
  </div>
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{(str(avg_score) + '%') if avg_score is not None else '-'}</div>
    <div class="ha-kpi-lbl">평균 정답률</div>
  </div>
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{_num(recent_cnt)}</div>
    <div class="ha-kpi-lbl">최근 7일 학습</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ✅ 최근 7일 학습
    _render_week_widget(attempts)




    # 추천 1줄(규칙 기반)
    rec = None
    # 반복오답(3회+)가 많으면 TOP10 추천
    try:
        from collections import Counter
        _cc = Counter([(w.get("jp_word") or "").strip() for w in (wrongs or []) if (w.get("jp_word") or "").strip()])
        rep3 = sum(1 for k,v in _cc.items() if v >= 3)
    except Exception:
        rep3 = 0
    if rep3 >= 5:
        rec = "🔥 반복 오답이 쌓였어요. 오늘은 TOP10 복습부터 가볍게 정리해볼까요?"
    elif wk.get("회화", 0) == 0:
        rec = "🗣 이번 주 회화가 0회예요. 회화 1세트만 해도 감이 확 살아납니다."
    elif wk.get("단어", 0) == 0:
        rec = "📚 이번 주 단어 풀이가 0회예요. 단어 5문제만 풀어도 루틴이 유지돼요."
    elif wk.get("한자", 0) == 0:
        rec = "🈶 이번 주 한자 풀이가 0회예요. 한자 5문제만 가볍게!"
    else:
        rec = "✅ 흐름이 좋아요. 오늘은 오답 TOP10으로 마무리하면 완벽합니다."

    if rec:
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        st.info(rec)

        # 🔥 TOP10 복습 시작(반복오답 3회+ 우선, 없으면 최근오답)
        if st.button("🔥 TOP10 복습 시작", use_container_width=True, key="myp_top10_start"):
            # 우선순위: 반복(3회+) → 최근
            # jp_word 기준으로 묶어 Top10 선정
            def _dt(w):
                return _to_dt_kst(w.get("created_at")) or datetime.min.replace(tzinfo=timezone(timedelta(hours=9)))

            try:
                from collections import defaultdict
                groups = defaultdict(list)
                for w in (wrongs or []):
                    jp = (w.get("jp_word") or w.get("question") or "").strip()
                    if jp:
                        groups[jp].append(w)

                # 반복 후보(3회+)
                rep = []
                for jp, ws in groups.items():
                    if len(ws) >= 3:
                        latest = max(ws, key=_dt)
                        rep.append((len(ws), _dt(latest), latest))

                rep.sort(key=lambda x: (-x[0], -x[1].timestamp()))
                chosen = [t[2] for t in rep][:10]

                if len(chosen) < 10:
                    # 최근 오답으로 채우기(중복 jp 제외)
                    used = set((w.get("jp_word") or w.get("question") or "").strip() for w in chosen)
                    recent = sorted([w for w in (wrongs or []) if (w.get("jp_word") or w.get("question") or "").strip() and ((w.get("jp_word") or w.get("question") or "").strip() not in used)],
                                    key=_dt, reverse=True)
                    for w in recent:
                        if len(chosen) >= 10:
                            break
                        jp = (w.get("jp_word") or w.get("question") or "").strip()
                        if jp and jp not in used:
                            chosen.append(w)
                            used.add(jp)

                if chosen:
                    st.session_state["myp_wrong_quiz"] = _make_wrong_quiz(chosen, n=min(10, len(chosen)))
                    st.session_state["myp_wrong_quiz_ans"] = {}
                    st.session_state["myp_wrong_quiz_done"] = False
                    st.toast("TOP10 복습을 시작합니다.")
                    st.rerun()
                else:
                    st.info("아직 저장된 오답이 없습니다.")
            except Exception:
                st.info("오답을 불러오는 중 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.")

    st.markdown("</div>", unsafe_allow_html=True)
# ---------------------------
# Views
# ---------------------------
def _render_wrongs(wrongs: List[Dict[str, Any]], wrongs_table: str = "") -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📚 오답</div><div class="ha-sub">앱 선택 + 검색 + 반복오답 토글 + 접힘 목록.</div>', unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답이 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ✅ 오답으로 시험보기 (단어/한자/회화로 세분화)
    colQ1, colQ2 = st.columns([7, 3], vertical_alignment="center")
    with colQ1:
        st.markdown("**오답으로 시험보기**", help="단어/한자/회화 중 원하는 유형만 골라 시험을 볼 수 있어요.")
        quiz_app = st.radio(
            "유형",
            options=["단어", "한자", "회화"],
            horizontal=True,
            label_visibility="collapsed",
            key="myp_wrong_quiz_app",
        )
    with colQ2:
        quiz_n = st.selectbox("문항 수", options=[5, 10, 15, 20], index=1, key="myp_wrong_quiz_n")

    # ✅ 선택한 앱만 필터 (app / quiz_type 둘 다 지원)
    # - hotena_basic.py: quiz_type='word' (app 컬럼이 없는 경우가 많음)
    # - talk.py: quiz_type='talk'
    # - 일부 스키마: app='word'/'kanji'/'talk' 등
    def _wrong_app_label(w: Dict[str, Any]) -> str:
        try:
            qt = (w.get("quiz_type") or w.get("type") or w.get("quiz") or "").lower().strip()
            ap = (w.get("app") or "").lower().strip()
            # quiz_type 우선
            if qt in ("word", "vocab", "vocabulary"):
                return "단어"
            if qt in ("kanji",):
                return "한자"
            if qt in ("talk", "conversation", "speaking"):
                return "회화"
            # app fallback
            return _app_label(ap)
        except Exception:
            return "단어"

    wrongs_for_quiz = [w for w in wrongs if _wrong_app_label(w) == quiz_app]

    if st.button("📝 오답으로 시험보기", use_container_width=True, key="myp_wrong_quiz_start"):
        if not wrongs_for_quiz:
            st.info(f"""{quiz_app}에서 최근 오답이 없어요. 🙂

상단 필터를 바꾸거나, 해당 훈련에서 먼저 문제를 풀어보세요.""")
        else:
            st.session_state["myp_wrong_quiz"] = _build_wrong_quiz_for_app(quiz_app, wrongs_for_quiz, int(quiz_n))
            st.session_state["myp_wrong_quiz_ans"] = {}
            st.session_state["myp_wrong_quiz_done"] = False
            st.rerun()

    quiz = st.session_state.get("myp_wrong_quiz") or []
    # 버튼을 눌렀는데 문제가 생성되지 않는 경우(뜻 데이터 없음 등)
    if ("myp_wrong_quiz" in st.session_state) and (not quiz):
        st.info("시험을 만들 수 있는 오답이 부족합니다. (뜻/정답 텍스트 컬럼이 비어있을 수 있어요.)")
    if quiz:
        st.markdown('<div class="ha-card" style="padding:12px 12px;">', unsafe_allow_html=True)
        st.markdown('<div class="ha-card-title">오답 시험</div>', unsafe_allow_html=True)

        # ✅ radio 선택으로 매번 rerun 되지 않도록: 폼으로 감싸서 "채점하기" 때만 제출/채점
        prev_ans = st.session_state.get("myp_wrong_quiz_ans") or {}

        with st.form("myp_wrong_quiz_form", clear_on_submit=False):
            for i, qitem in enumerate(quiz, start=1):
                title = f"**{i}. {qitem['jp_word']}**"
                if qitem.get("reading"):
                    title += f"  _( {qitem.get('reading')} )_"
                st.markdown(title)

                opts = qitem["options"]
                st.radio(
                    "선택",
                    options=opts,
                    index=opts.index(prev_ans[i]) if (i in prev_ans and prev_ans[i] in opts) else None,
                    key=f"mq_{i}",
                    label_visibility="collapsed",
                    disabled=bool(st.session_state.get("myp_wrong_quiz_done")),
                )

            submitted = st.form_submit_button("채점하기", use_container_width=True)

        # ✅ 제출(채점) 버튼을 눌렀을 때만 답을 모아 저장 + done 처리
        if submitted:
            ans = {}
            for i in range(1, len(quiz) + 1):
                ans[i] = st.session_state.get(f"mq_{i}")
            st.session_state["myp_wrong_quiz_ans"] = ans
            st.session_state["myp_wrong_quiz_done"] = True
            st.rerun()

        # 닫기 버튼은 폼 밖(즉시 동작)
        if st.button("시험 닫기", use_container_width=True, key="myp_wrong_quiz_close"):
            st.session_state["myp_wrong_quiz"] = []
            st.session_state["myp_wrong_quiz_ans"] = {}
            st.session_state["myp_wrong_quiz_done"] = False
            for i in range(1, len(quiz) + 1):
                st.session_state.pop(f"mq_{i}", None)
            st.rerun()

        # ✅ 결과표시는 세션에 저장된 답으로 계산
        if st.session_state.get("myp_wrong_quiz_done"):
            ans = st.session_state.get("myp_wrong_quiz_ans") or {}
            correct_cnt = 0
            for i, qitem in enumerate(quiz, start=1):
                if ans.get(i) == qitem["correct"]:
                    correct_cnt += 1
            st.success(f"점수: {correct_cnt}/{len(quiz)}")
            with st.expander("오답만 보기", expanded=False):
                for i, qitem in enumerate(quiz, start=1):
                    if ans.get(i) != qitem["correct"]:
                        st.markdown(
                            f"- **{i}. {qitem['jp_word']}** → 정답: **{qitem['correct']}** / 선택: {ans.get(i)}"
                        )

        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()

    counts: Dict[str, int] = {}
    for w in wrongs:
        k = (w.get("jp_word") or "").strip()
        if k:
            counts[k] = counts.get(k, 0) + 1
    # 앱 선택(전체/단어/한자/회화) + 정렬/표시개수는 아래에서 구성
    q = st.text_input("검색 (단어/뜻/발음)", value=st.session_state.get("myp_wrongs_q", ""), key="myp_wrongs_q")
    only_repeat = st.toggle("🔥 반복 오답만 보기 (3회+)", value=st.session_state.get("myp_wrongs_repeat", False), key="myp_wrongs_repeat")

    # ✅ 앱 필터(버튼 그룹) — 한 줄 고정(줄바꿈 방지)
    if "myp_wrongs_app_quick" not in st.session_state:
        st.session_state["myp_wrongs_app_quick"] = "전체"
    _app_now = st.session_state.get("myp_wrongs_app_quick", "전체")

    b1, b2, b3, b4 = st.columns(4, gap="small")
    def _app_btn(label: str, col):
        selected = (_app_now == label)
        if col.button(label, use_container_width=True, type=("primary" if selected else "secondary"), key=f"myp_wrongs_appbtn_{label}"):
            st.session_state["myp_wrongs_app_quick"] = label
            st.rerun()

    _app_btn("전체", b1)
    _app_btn("단어", b2)
    _app_btn("한자", b3)
    _app_btn("회화", b4)

    # ✅ 정렬 + 표시개수 (앱 버튼 아래로 내려서 깔끔하게)
    c_sort, c_per = st.columns([1, 1], gap="small")
    with c_sort:
        sort_mode = st.selectbox("정렬", ["최근순", "반복순", "오래된순"], index=0, key="myp_wrongs_sort")
    with c_per:
        per_page = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100], value=10, key="myp_wrongs_per")

    app_quick = st.session_state.get("myp_wrongs_app_quick", "전체")
    app_selected = [] if app_quick == "전체" else [app_quick]

    def match(w: Dict[str, Any]) -> bool:
        jp = (w.get("jp_word") or "").lower()
        rd = (w.get("reading") or "").lower()
        mn = (w.get("meaning") or "").lower()
        if q.strip():
            qq = q.strip().lower()
            if qq not in jp and qq not in rd and qq not in mn:
                return False
        if only_repeat and counts.get((w.get("jp_word") or "").strip(), 0) < 3:
            return False
        if app_selected and _wrong_app_label(w) not in app_selected:
            return False
        return True

    
    filtered = [w for w in wrongs if match(w)]
    if not filtered:
        if app_quick != "전체":
            st.info(f"{app_quick}에서 조건에 맞는 오답이 없습니다. 🙂")
        else:
            st.info("조건에 맞는 오답이 없습니다. 🙂")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ✅ 정렬
    def _ca(w):
        return _to_dt_kst(w.get("created_at")) or datetime(1970,1,1,tzinfo=timezone(timedelta(hours=9)))
    if sort_mode == "오래된순":
        filtered = sorted(filtered, key=_ca)  # asc
    elif sort_mode == "반복순":
        filtered = sorted(filtered, key=lambda w: (-(counts.get((w.get("jp_word") or "").strip(), 0)), _ca(w)), reverse=False)
    else:
        filtered = sorted(filtered, key=_ca, reverse=True)

    repeat_cnt = sum(1 for w in filtered if counts.get((w.get("jp_word") or "").strip(), 0) >= 3)

    # ✅ "더 보기" 리스트 시그니처 (필터/검색/표시개수 변경 시 표시 개수 리셋)
    _sig = (
        str(app_selected),
        str(q or "").strip().lower(),
        bool(only_repeat),
        int(per_page),
        str(sort_mode),
    )
    if st.session_state.get("myp_wrongs_sig") != _sig:
        st.session_state["myp_wrongs_sig"] = _sig
        st.session_state["myp_wrongs_show_n"] = int(per_page)

    show_n = int(st.session_state.get("myp_wrongs_show_n", per_page) or per_page)
    show_n = max(int(per_page), show_n)
    show_n = min(len(filtered), show_n)

    # ✅ 상단 요약 칩(한 줄 정렬): 총 / 반복오답 / 표시
    st.markdown(
        f'<div class="ha-meta" style="margin-top:0; margin-bottom:12px;">'
        f'<span class="ha-chip">총 <b>{_num(len(filtered))}</b>개</span>'
        f'<span class="ha-chip">반복 오답 <b>{_num(repeat_cnt)}</b>개</span>'
        f'<span class="ha-chip">표시 <b>{_num(show_n)}</b> / <b>{_num(len(filtered))}</b></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 표시 목록
    chunk = filtered[:show_n]


    for w in chunk:
        jp = w.get("jp_word") or "-"
        app = _app_label(w.get("app"))
        level = w.get("level") or "-"
        dt = _fmt_dt(w.get("created_at"))
        rep = counts.get((w.get("jp_word") or "").strip(), 0)
        header = f"{jp}  ·  {app}  ·  Lv {level}" + (f"  ·  🔥 {rep}회" if rep >= 3 else "")
        with st.expander(header, expanded=False):
            c1, c2 = st.columns([2, 2])
            with c1:
                st.markdown(f"**정답**: {w.get('correct_answer') or '-'}")
                st.markdown(f"**내답**: {w.get('user_answer') or '-'}")
            with c2:
                st.markdown(f"**발음**: {w.get('reading') or '-'}")
                st.markdown(f"**뜻**: {w.get('meaning') or '-'}")
            st.caption(f"저장: {dt}")


    # ✅ 더 보기 버튼 (10개씩 추가)
    if show_n < len(filtered):
        c_more1, c_more2, c_more3 = st.columns([1, 2, 1])
        with c_more2:
            if st.button("더 보기 (+10개)", key="myp_wrongs_more", use_container_width=True):
                st.session_state["myp_wrongs_show_n"] = min(len(filtered), show_n + 10)
                st.rerun()
    else:
        st.caption("끝까지 다 봤어요 🙂")

    
    # ✅ 회화: 내 문장 모아보기(최근 20개)
    with st.expander("🗣 내 문장 모아보기 (최근 20개)", expanded=False):
        talk_lines = []
        for w in (wrongs or []):
            if _wrong_app_label(w) == "회화":
                ua = (w.get("user_answer") or w.get("answer") or "").strip()
                if ua:
                    talk_lines.append(ua)
        talk_lines = talk_lines[:20]
        if not talk_lines:
            st.caption("저장된 회화 문장이 아직 없습니다.")
        else:
            for i, line in enumerate(talk_lines, start=1):
                st.markdown(f"{i}. {line}")

st.markdown("</div>", unsafe_allow_html=True)


def _render_records(attempts: List[Dict[str, Any]], attempts_status: str) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📈 기록</div><div class="ha-sub">최근 3개 + 빠른 목록(중복 제거). app + 품사(pos)를 깔끔히 표시합니다.</div>', unsafe_allow_html=True)

    if attempts_status != "ok" or not attempts:
        st.warning("학습 기록을 불러올 수 없습니다. (RLS 또는 테이블/컬럼 확인)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    attempts = [_normalize_attempt(a) for a in attempts]

    app_selected = _render_filter_chips("앱 필터", "myp_rec_app")
    level_q = st.text_input("레벨 검색 (예: N4, 4 등)", value=st.session_state.get("myp_rec_lvlq", ""), key="myp_rec_lvlq")

    def match(a: Dict[str, Any]) -> bool:
        if app_selected and _app_label(a.get("app")) not in app_selected:
            return False
        if level_q.strip():
            lv = str(a.get("level") or "").lower()
            if level_q.strip().lower() not in lv:
                return False
        return True

    filtered = [a for a in attempts if match(a)]

    scores = [s for s in (_calc_score(a) for a in filtered[:200]) if s is not None]
    best = max(scores) if scores else None
    avg = round(sum(scores) / len(scores), 1) if scores else None

    now = datetime.now(timezone(timedelta(hours=9)))
    week_ago = now - timedelta(days=7)
    recent7 = [a for a in filtered if (dt := _to_dt_kst(a.get("created_at"))) and dt >= week_ago]

    st.markdown(
        f"""
<div class="ha-meta">
  <span class="ha-chip">총 <b>{_num(len(filtered))}</b>회</span>
  <span class="ha-chip">최근 7일 <b>{_num(len(recent7))}</b>회</span>
  <span class="ha-chip">평균 <b>{(str(avg)+'%') if avg is not None else '-'}</b></span>
  <span class="ha-chip">최고 <b>{(str(best)+'%') if best is not None else '-'}</b></span>
</div>
""",
        unsafe_allow_html=True,
    )

    _render_week_widget(filtered)
    st.divider()

    st.markdown("**최근 학습(3개)**")
    top = filtered[:3]
    for a in top:
        app = _app_label(a.get("app"))
        pos = _pos_label(a.get("pos"))
        level = a.get("level") or "-"
        dt = _fmt_dt(a.get("created_at"))
        score = _calc_score(a)
        total, wrong = _calc_total_wrong(a)

        title = f"{app}" + (f" · {pos}" if pos else "") + (f" · Lv {level}" if level != "-" and str(level).strip() else "")

        st.markdown(
            f"""
<div class="ha-card">
  <div class="ha-card-title">{title}</div>
  <div class="ha-meta">
    <span class="ha-chip">{dt}</span>
    <span class="ha-chip">점수 <b>{(str(score)+'%') if score is not None else '-'}</b></span>
    <span class="ha-chip">문항 <b>{total}</b></span>
    <span class="ha-chip">오답 <b>{wrong}</b></span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.divider()

    st.markdown("**빠른 목록**")
    show_n = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100, 200], value=30, key="myp_rec_n")
    rest = filtered[3:]
    for a in rest[:show_n]:
        app = _app_label(a.get("app"))
        pos = _pos_label(a.get("pos"))
        level = a.get("level") or ""
        dt = _fmt_dt(a.get("created_at"))
        score = _calc_score(a)
        total, wrong = _calc_total_wrong(a)

        # ✅ 타이틀에서 앱/품사만 1회 표시 (중복 제거)

        title = f"{app}" + (f" · {pos}" if pos else "")


        # ✅ 메타에는 날짜/점수/문항/오답만

        meta_html = (

            f"<span class='chip'>{dt}</span> "

            + f"<span class='chip'>점수 <b>{(str(score)+'%') if score is not None else '-'}</b></span> "

            + f"<span class='chip'>문항 <b>{total}</b></span> "

            + f"<span class='chip'>오답 <b>{wrong}</b></span>"

        )

        components.html(_card_iframe_html(title, meta_html), height=88, scrolling=False)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_msgs(msgs: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="ha-card ha-msg-card">', unsafe_allow_html=True)
    st.markdown('<div class="ha-card-title">메시지</div>', unsafe_allow_html=True)

    if not msgs:
        st.info("새 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total = len(msgs)
    unread = sum(1 for x in msgs if not x.get("read_at"))
    st.markdown(
        f"""
<div class="ha-inline" style="margin-top:6px;">
  <span class="ha-chip">총 <b>{total}</b> 개</span>
  <span class="ha-chip">읽지 않음 <b>{unread}</b> 개</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ha-msg-gap"></div>', unsafe_allow_html=True)

    show_unread_only = st.toggle("읽지 않은 것만 보기", value=False, key="myp_msg_unread_only")
    per = st.slider("표시 개수", min_value=5, max_value=50, value=20, step=5, key="myp_msg_per")

    filtered = [x for x in msgs if (not show_unread_only) or (not x.get("read_at"))]
    sb = _sb()

    st.markdown('<div class="ha-msg-scope">', unsafe_allow_html=True)

    for mm in filtered[:per]:
        mid = mm.get("id")
        title = (mm.get("title") or "메시지").strip()
        body = (mm.get("body") or "").strip()
        dt = _fmt_dt(mm.get("created_at") or "")
        is_unread = not mm.get("read_at")
        chip = "읽지 않음" if is_unread else "읽음"
        dot = "● " if is_unread else ""

        label = f"{dot}{title} · {dt} · {chip}"

        with st.expander(label, expanded=False):
            safe_body = _escape_html(body).replace("\n", "<br>")
            st.markdown(
                f'<div class="ha-msg-bodyA"><div class="ha-msg-bodyA-inner">{safe_body}</div></div>',
                unsafe_allow_html=True,
            )

            if is_unread and sb and mid:
                if st.button("읽음 처리", key=f"msg_read_{mid}", use_container_width=True):
                    try:
                        sb.table("user_messages").update({"read_at": datetime.utcnow().isoformat()}).eq("id", mid).execute()
                        st.success("읽음 처리 완료")
                        st.rerun()
                    except Exception:
                        st.warning("읽음 처리에 실패했습니다. (RLS 확인)")

        # (spacing fix) wrapper div removed
        # wrapper

    st.markdown("</div>", unsafe_allow_html=True)  # scope
    st.markdown("</div>", unsafe_allow_html=True)  # card


def render() -> None:
    _inject_css()
    _wrap_start()

    wrongs, wrongs_table = _load_wrongs(limit=400)
    msgs = _load_messages(limit=300)
    attempts, attempts_status = _load_attempts(limit=500)
    attempts_ok = attempts if attempts_status == "ok" else []
    attempts_ok = [_normalize_attempt(a) for a in attempts_ok]

    _render_top_summary(wrongs, attempts_ok)

    # ✅ 탭 방식 (요청 사항)
    tab_w, tab_r, tab_m = st.tabs(["📚 오답", "📈 기록", "📩 메시지"])
    with tab_w:
        _render_wrongs(wrongs, wrongs_table)
    with tab_r:
        _render_records(attempts_ok, "ok" if attempts_ok else attempts_status)
    with tab_m:
        _render_msgs(msgs)

    _wrap_end()
