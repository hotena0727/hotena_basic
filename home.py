from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# ✅ 빈 components.html iframe(회색 블록) 자동 제거 (mypage 포함)
# ============================================================
try:
    import streamlit.components.v1 as components
    components.html("""
<script>
(function(){
  function cleanEmptyHtmlIframes(){
    try{
      var doc = (window.parent && window.parent.document) ? window.parent.document : document;
      var iframes = doc.querySelectorAll('iframe[title="streamlit.components.v1.html"]');
      iframes.forEach(function(fr){
        try{
          var cd = fr.contentDocument;
          if(!cd || !cd.body) return;
          var kids = Array.from(cd.body.children || []);
          var nonScript = kids.filter(function(el){
            var t = (el.tagName||'').toUpperCase();
            return t !== 'SCRIPT' && t !== 'STYLE';
          });
          var text = (cd.body.textContent || '').trim();
          if(nonScript.length === 0 && text === ''){
            fr.style.height = '0px';
            fr.style.minHeight = '0px';
            fr.style.display = 'none';
            var wrap = fr.closest('[data-testid="stIFrame"]') || fr.parentElement;
            if(wrap){
              wrap.style.height = '0px';
              wrap.style.minHeight = '0px';
              wrap.style.margin = '0';
              wrap.style.padding = '0';
              wrap.style.display = 'none';
            }
          }
        }catch(e){}
      });
    }catch(e){}
  }

  cleanEmptyHtmlIframes();
  setTimeout(cleanEmptyHtmlIframes, 80);
  setTimeout(cleanEmptyHtmlIframes, 250);
  setTimeout(cleanEmptyHtmlIframes, 700);

  var n = 0;
  var iv = setInterval(function(){
    cleanEmptyHtmlIframes();
    n++;
    if(n >= 20) clearInterval(iv);
  }, 450);
})();
</script>
""", height=0)
except Exception:
    pass


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
    """오답 테이블명이 환경마다 달라질 수 있어 자동 탐색합니다.
    - 테이블 후보를 순회하고, 컬럼 지정 조회가 실패하면 '*' 조회로 재시도합니다.
    - 필드명이 다른 경우(alias)도 최대한 흡수합니다.
    """
    # 1차: 흔한 컬럼 세트
    cols1 = "id, user_id, app, pos, level, jp_word, word, term, reading, yomi, kana, meaning, meaning_kr, kr_meaning, correct_answer, correct, user_answer, answer, created_at"
    for table in ("wrong_notes", "wrong_note", "wrongs"):
        rows = _safe_select(table, cols=cols1, limit=limit, order="created_at", desc=True)
        if not rows:
            # 2차: 스키마가 달라 cols select가 실패하는 환경을 대비 → 전체 조회
            rows = _safe_select(table, cols="*", limit=limit, order="created_at", desc=True)
        if rows:
            for r in rows:
                # jp_word / word / term
                if not r.get("jp_word"):
                    r["jp_word"] = r.get("word") or r.get("term") or r.get("jp") or r.get("question")
                # reading
                if not r.get("reading"):
                    r["reading"] = r.get("yomi") or r.get("kana") or r.get("furigana")
                # meaning
                if not r.get("meaning"):
                    r["meaning"] = r.get("meaning_kr") or r.get("kr_meaning") or r.get("ko_meaning")
                # correct / user answer
                if "correct_answer" not in r or r.get("correct_answer") in (None, ""):
                    r["correct_answer"] = r.get("correct_answer") or r.get("correct") or r.get("gold") or r.get("target")
                if "user_answer" not in r or r.get("user_answer") in (None, ""):
                    r["user_answer"] = r.get("user_answer") or r.get("answer") or r.get("pred") or r.get("user")
            # user별 필터가 필요할 수 있음 (RLS로 처리되는 경우가 많아서 여기서는 건드리지 않음)
            return rows, table
    return [], "wrong_notes"
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
    sb = _sb()
    try:
        if sb and hasattr(sb, "auth") and hasattr(sb.auth, "sign_out"):
            sb.auth.sign_out()
    except Exception:
        pass

    for k in [
        "access_token", "refresh_token", "user_id", "uid", "email",
        "sb_authed", "sb", "is_admin", "plan", "user_plan"
    ]:
        if k in st.session_state:
            st.session_state[k] = None

    for key in ("hub_page", "page", "current_page"):
        if key in st.session_state:
            st.session_state[key] = "home"
    st.rerun()


# ---------------------------
# Mini widget
# ---------------------------
def _week_counts(attempts: List[Dict[str, Any]]) -> Tuple[List[datetime], List[int]]:
    now = datetime.now(timezone(timedelta(hours=9)))
    days = [(now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0) for i in range(6, -1, -1)]
    counts = [0] * 7
    for a in attempts:
        dt = _to_dt_kst(a.get("created_at"))
        if not dt:
            continue
        d0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for i, day in enumerate(days):
            if d0 == day:
                counts[i] += 1
                break
    return days, counts


def _render_week_widget(attempts: List[Dict[str, Any]]) -> None:
    days, counts = _week_counts(attempts)
    mx = max(counts) if counts else 0
    dow_kr = ["월", "화", "수", "목", "금", "토", "일"]

    blocks = []
    for day, c in zip(days, counts):
        wd = dow_kr[day.weekday()]
        if mx <= 0:
            bg = "rgba(30,107,255,0.06)"
            bd = "rgba(229,231,235,1)"
        else:
            alpha = 0.08 + (0.20 * (c / mx)) if c > 0 else 0.06
            bg = f"rgba(30,107,255,{alpha:.3f})"
            bd = "rgba(30,107,255,0.22)" if c > 0 else "rgba(229,231,235,1)"
        blocks.append(
            f"""
<div class="ha-day" style="background:{bg}; border-color:{bd};">
  <div class="ha-day-top">{wd}</div>
  <div class="ha-day-num">{day.day}</div>
  <div class="ha-day-sub">{c}회</div>
</div>
"""
        )

    total = sum(counts)
    streak = 0
    for c in reversed(counts):
        if c > 0:
            streak += 1
        else:
            break

    st.markdown(
        f"""
<div class="ha-week">
  <div class="ha-week-head">
    <div class="ha-week-title">최근 7일 학습</div>
    <div class="ha-inline">
      <span class="ha-chip">총 <b>{total}</b>회</span>
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

    colA, colB = st.columns([7, 3], vertical_alignment="center")
    with colB:
        b1, b2 = st.columns(2, gap="small")
        with b1:
            if st.button("🏠 홈", use_container_width=True, key="myp_v4_home"):
                _go_home()
        with b2:
            if st.button("로그아웃", use_container_width=True, key="myp_v4_logout"):
                _logout()

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

    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
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

    _render_week_widget(attempts)
    st.markdown("</div>", unsafe_allow_html=True)
# ---------------------------
# Views
# ---------------------------
def _render_wrongs(wrongs: List[Dict[str, Any]], wrongs_table: str = "") -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📚 오답</div><div class="ha-sub">앱 필터(칩) + 검색 + 반복오답 토글 + 접힘 목록.</div>', unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답이 없습니다.")
        if wrongs_table:
            st.caption(f"시도한 테이블: wrong_notes → wrong_note → wrongs (현재: {wrongs_table})")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ✅ 오답으로 시험보기 (요청 사항)
    colQ1, colQ2 = st.columns([7, 3], vertical_alignment="center")
    with colQ1:
        pass
    with colQ2:
        quiz_n = st.selectbox("시험 문항 수", options=[5, 10, 15, 20], index=1, key="myp_wrong_quiz_n")

    if st.button("📝 오답으로 시험보기", use_container_width=True, key="myp_wrong_quiz_start"):
        st.session_state["myp_wrong_quiz"] = _make_wrong_quiz(wrongs, n=int(quiz_n))
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
        ans = st.session_state.get("myp_wrong_quiz_ans") or {}
        for i, qitem in enumerate(quiz, start=1):
            title = f"**{i}. {qitem['jp_word']}**"
            if qitem.get("reading"):
                title += f"  _( {qitem.get('reading')} )_"
            st.markdown(title)
            opts = qitem["options"]
            ans[i] = st.radio(
                "선택",
                options=opts,
                index=opts.index(ans[i]) if i in ans and ans[i] in opts else 0,
                key=f"mq_{i}",
                label_visibility="collapsed",
            )
        st.session_state["myp_wrong_quiz_ans"] = ans

        c1, c2 = st.columns([1, 1], gap="small")
        with c1:
            if st.button("채점하기", use_container_width=True, key="myp_wrong_quiz_grade"):
                st.session_state["myp_wrong_quiz_done"] = True
                st.rerun()
        with c2:
            if st.button("시험 닫기", use_container_width=True, key="myp_wrong_quiz_close"):
                st.session_state["myp_wrong_quiz"] = []
                st.session_state["myp_wrong_quiz_ans"] = {}
                st.session_state["myp_wrong_quiz_done"] = False
                st.rerun()

        if st.session_state.get("myp_wrong_quiz_done"):
            correct_cnt = 0
            for i, qitem in enumerate(quiz, start=1):
                if ans.get(i) == qitem["correct"]:
                    correct_cnt += 1
            st.success(f"점수: {correct_cnt}/{len(quiz)}")
            with st.expander("오답만 보기", expanded=False):
                for i, qitem in enumerate(quiz, start=1):
                    if ans.get(i) != qitem["correct"]:
                        st.markdown(f"- **{i}. {qitem['jp_word']}** → 정답: **{qitem['correct']}** / 선택: {ans.get(i)}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()

    counts: Dict[str, int] = {}
    for w in wrongs:
        k = (w.get("jp_word") or "").strip()
        if k:
            counts[k] = counts.get(k, 0) + 1

    app_selected = _render_filter_chips("앱 필터", "myp_wrongs_app")
    q = st.text_input("검색 (단어/뜻/발음)", value=st.session_state.get("myp_wrongs_q", ""), key="myp_wrongs_q")
    only_repeat = st.toggle("🔥 반복 오답만 보기 (3회+)", value=st.session_state.get("myp_wrongs_repeat", False), key="myp_wrongs_repeat")
    per_page = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100], value=20, key="myp_wrongs_per")

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
        if app_selected and _app_label(w.get("app")) not in app_selected:
            return False
        return True

    filtered = [w for w in wrongs if match(w)]
    repeat_cnt = sum(1 for w in filtered if counts.get((w.get("jp_word") or "").strip(), 0) >= 3)
    st.markdown(
        f'<div class="ha-meta"><span class="ha-chip">총 <b>{_num(len(filtered))}</b>개</span>'
        f'<span class="ha-chip">반복 오답 <b>{_num(repeat_cnt)}</b>개</span></div>',
        unsafe_allow_html=True,
    )

    max_page = max(1, (len(filtered) + per_page - 1) // per_page)
    page = st.number_input("페이지", min_value=1, max_value=max_page, value=min(st.session_state.get("myp_wrongs_page", 1), max_page), step=1, key="myp_wrongs_page")
    start = (page - 1) * per_page
    chunk = filtered[start:start + per_page]

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
