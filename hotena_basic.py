import streamlit as st

# ============================================================
# ✅ 이하: 기존 세션 상태 초기화/shape ensure (그대로 유지)
# ============================================================

if "quiz_version" not in st.session_state:
    st.session_state.quiz_version = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []
if "saved_this_attempt" not in st.session_state:
    st.session_state.saved_this_attempt = False
if "stats_saved_this_attempt" not in st.session_state:
    st.session_state.stats_saved_this_attempt = False
if "session_stats_applied_this_attempt" not in st.session_state:
    st.session_state.session_stats_applied_this_attempt = False
if "history" not in st.session_state:
    st.session_state.history = []
if "progress_dirty" not in st.session_state:
    st.session_state.progress_dirty = False
if "wrong_counter" not in st.session_state:
    st.session_state.wrong_counter = {}
if "total_counter" not in st.session_state:
    st.session_state.total_counter = {}

ensure_mastered_words_shape()
ensure_excluded_wrong_words_shape()
ensure_mastery_banner_shape()


# ============================================================
# ✅ 상단 UI: 품사 버튼 → (기타 expander + 적용 버튼) → 유형 버튼 → 캡션 → divider
# ============================================================
def on_pick_pos_group(ps: str):
    ps = str(ps).strip().lower()
    if ps == st.session_state.pos_group:
        return
    st.session_state.pos_group = ps

    # ✅ 제한 그룹이면 reading 선택 상태를 자동 해제
    if ps in POS_ONLY_2TYPES and st.session_state.quiz_type == "reading":
        st.session_state.quiz_type = "meaning"

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
    st.session_state["_scroll_top_once"] = True

def on_pick_qtype(qt: str):
    qt = str(qt).strip()
    if qt == st.session_state.quiz_type:
        return
    st.session_state.quiz_type = qt

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    st.session_state["_scroll_top_once"] = True

# ✅ 현재 pos_group 기준으로 유형 리스트 재계산(표시 직전에!)
try:
    if sb_authed is not None:
        available_types = get_available_quiz_types_for_pos(st.session_state.get("pos_group", "noun"))
    else:
        g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
        available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER
except Exception:
    g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
    available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER

# ✅ 선택된 유형이 현재 pos_group에서 허용되지 않으면 meaning으로 강제
if st.session_state.get("quiz_type") not in available_types:
    st.session_state.quiz_type = "meaning"

st.markdown('<div class="qtypewrap">', unsafe_allow_html=True)

st.markdown('<div class="qtype_hint jp">✨품사를 선택하세요</div>', unsafe_allow_html=True)

# ✅ 품사 그룹 버튼(5개)
pos_cols = st.columns(5, gap="small")
for i, ps in enumerate(POS_GROUP_OPTIONS):
    with pos_cols[i]:
        is_sel = (ps == st.session_state.pos_group)
        st.button(
            ("✅ " if is_sel else "") + POS_LABEL_MAP.get(ps, ps),
            use_container_width=True,
            type=("primary" if is_sel else "secondary"),
            key=f"btn_posg_{ps}",
            on_click=on_pick_pos_group,
            args=(ps,),
        )

# ✅ B안: 기타 선택 시에만 세부 선택 expander + 적용 버튼
if st.session_state.pos_group == "other":
    with st.expander("기타 세부 선택 (부사/조사/접속사/감탄사)", expanded=True):
        cols = st.columns(2)
        for j, p in enumerate(OTHER_POS_OPTIONS):
            with cols[j % 2]:
                checked = (p in st.session_state.other_pos_selected)
                new_checked = st.checkbox(OTHER_POS_LABEL_MAP[p], value=checked, key=f"chk_other_{p}")
                if new_checked:
                    st.session_state.other_pos_selected.add(p)
                else:
                    st.session_state.other_pos_selected.discard(p)

        if st.button("🔄 기타 선택 적용(새 문제)", use_container_width=True, key="btn_apply_other"):
            # ✅ 기타는 reading 불가
            if st.session_state.quiz_type == "reading":
                st.session_state.quiz_type = "meaning"

            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

st.markdown('<div class="qtype_hint jp">✨유형을 선택하세요</div>', unsafe_allow_html=True)

# ✅ 유형 버튼
type_cols = st.columns(len(available_types), gap="small")
for i, qt in enumerate(available_types):
    with type_cols[i]:
        is_sel = (qt == st.session_state.quiz_type)
        st.button(
            ("✅ " if is_sel else "") + quiz_label_map.get(qt, qt),
            use_container_width=True,
            type=("primary" if is_sel else "secondary"),
            key=f"btn_qtype_{qt}",
            on_click=on_pick_qtype,
            args=(qt,),
        )

st.markdown("</div>", unsafe_allow_html=True)

# ✅ 필수패턴(카드)
with st.expander("📌 필수패턴 (카드로 빠르게 익히기)", expanded=False):
    if is_pro():
        render_pattern_cards()
    else:
        st.caption("🔒 PRO에서 품사별 패턴 카드 전체가 열립니다.")
        # 무료 체험: 1장만
        render_pattern_cards()

st.markdown('<div class="tight-divider">', unsafe_allow_html=True)
st.divider()
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ✅ FREE 사용량 기록 (현재는 제한 OFF라 no-op)
# ============================================================
def add_free_used(n: int):
    """FREE 제한을 다시 켤 때를 대비해 남겨둠. 현재는 아무 것도 하지 않음."""
    return

# ============================================================
# ✅ 버튼: 새 문제(랜덤10) / 맞힌 단어 제외 초기화  (복붙 버전)
#   - 기존 "쓸데없는 새 문제" 버튼 제거
#   - "🔄 새 문제(랜덤 10문항)"을 왼쪽(원래 자리)로 이동
# ============================================================

def should_lock_quiz() -> bool:
    if is_pro():
        return False
    return False  # FREE 제한 없앴으면 잠금 없음

locked = should_lock_quiz()

cbtn1, cbtn2 = st.columns(2)

with cbtn1:
    if st.button(
        "🔄 새 문제(랜덤 10문항)",
        use_container_width=True,
        key="btn_new_random_10",
        disabled=locked
    ):
        clear_question_widget_keys()
    
        # ✅ 새 퀴즈 시작 = 제출 카운트 플래그 리셋
        st.session_state["_counted_today"] = False

        # ✅ 콤보 알림 단계 리셋(오늘 최고 콤보 기록은 유지)
        st.session_state["combo_last_notice"] = 0
    
        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
        mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
        st.session_state["_scroll_top_once"] = True
        st.rerun()
        

def reset_mastery_current():
    k = mastery_key()
    st.session_state.setdefault("seen_words", {}).setdefault(k, set()).clear()
    st.session_state.setdefault("mastered_words", {}).setdefault(k, set()).clear()
    st.session_state.setdefault("excluded_wrong_words", {}).setdefault(k, set()).clear()
    st.session_state.setdefault("mastery_done", {})[k] = False
    st.session_state.setdefault("mastery_banner_shown", {})[k] = False

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    st.session_state["_scroll_top_once"] = True
    st.rerun()

with cbtn2:
    if st.button("맞힌 단어 제외 초기화", disabled=locked, use_container_width=True, key="btn_reset_mastery"):
        reset_mastery_current()


    # locked가 항상 False라면 이 캡션은 사실상 안 뜸(있어도 무방)
    if locked:
        st.caption("🔒 무료는 하루 30문항(3세트)까지입니다. PRO로 업그레이드하면 계속 풀 수 있어요.")

k_now = mastery_key()
if st.session_state.get("mastery_done", {}).get(k_now, False):
    st.success("🏆 이 품사/유형을 완전히 정복했어요!")

    
# ============================================================
# ✅ 퀴즈 생성(없으면 1회 자동 생성)
# ============================================================

k_now = mastery_key()  # ✅ 먼저!

if "quiz" not in st.session_state or not isinstance(st.session_state.quiz, list):
    st.session_state.quiz = []

is_mastered_done = bool(st.session_state.get("mastery_done", {}).get(k_now, False))

if (not is_mastered_done) and len(st.session_state.quiz) == 0:
    if is_locked:
        render_paywall(daily_solved)
        st.stop()

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group) or []
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)

if len(st.session_state.quiz) == 0:
    if bool(st.session_state.get("mastery_done", {}).get(k_now, False)):
        st.success("✅ 이 설정에서 새로 출제할 문제가 더 이상 없습니다.")
        st.caption("👉 ‘출제 이력 초기화(다시 시작)’를 누르거나, 다른 품사·유형을 선택해 주세요.")
        st.caption("👉 틀린 문제는 마이페이지에서 ‘틀린 문제만 다시 풀기’로 복습하세요~")
        st.stop()

    st.info("현재는 이 설정으로 낼 문제가 없어요. 다른 품사/유형으로 바꿔서 시작해 주세요.")
    st.stop()

quiz_len = len(st.session_state.quiz)
if "answers" not in st.session_state or not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != quiz_len:
    st.session_state.answers = [None] * quiz_len

if bool(st.session_state.get("mastery_done", {}).get(k_now, False)):
    st.stop()


def _esc_html(x) -> str:
    x = "" if x is None else str(x)
    return (x.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;"))


# ============================================================
# ✅ 오늘 목표(Progress) - 세션 기반 (DB 없이)
#   - 상단(1곳)만 사용
#   - 하단은 SHOW_BOTTOM_GOAL=False면 절대 렌더링 안 됨
# ============================================================

SHOW_BOTTOM_GOAL = False  # ✅ 하단을 완전히 숨기려면 False 유지

def get_today_done_count() -> int:
    return int(st.session_state.get("today_done", 0))

def add_done_count(n: int):
    st.session_state["today_done"] = get_today_done_count() + int(n)

def reset_today_done():
    st.session_state["today_done"] = 0

def get_today_goal_default() -> int:
    return 10

# ✅ 누적용 상태(필요하면 유지)
if "counted_qids" not in st.session_state:
    st.session_state["counted_qids"] = set()
if "is_graded" not in st.session_state:
    st.session_state["is_graded"] = False

def render_today_goal_progress():
    st.markdown("### 🎯 오늘 목표 진행률")

    goal = int(st.session_state.get("today_goal", get_today_goal_default()))
    done = get_today_done_count()

    ratio = 0.0 if goal <= 0 else min(max(done / goal, 0.0), 1.0)

    st.progress(ratio)
    st.caption(f"진행: **{done} / {goal}문항** ({int(ratio*100)}%)")

    if done >= goal and goal > 0:
        st.success("🔥 오늘 목표 달성!")

    if st.button("🔁 오늘 목표 리셋", use_container_width=True, key="btn_reset_today_goal"):
        reset_today_done()
        st.rerun()

    st.divider()

# ============================================================
# ✅ 하단 렌더링(숨김)
#   - 아래 조건부 블록만 남기고, "직접 호출"은 절대 하지 마세요.
# ============================================================

if SHOW_BOTTOM_GOAL:
    render_today_goal_progress()


# ============================================================
# ✅ 문제 표시 (동그란 배지: ① ② ③ ... + 같은 줄)
# ============================================================
circled_nums = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"

for idx, q in enumerate(st.session_state.quiz):
    badge = circled_nums[idx] if idx < len(circled_nums) else f"({idx+1})"

    st.markdown(
        f"""
<div class="jp" style="display:flex; align-items:baseline; gap:5px; margin: 10px 0 8px 0;">
  <div style="
    flex:0 0 auto;
    font-size:20px;
    line-height:1;
    font-weight:900;
    transform: translateY(1px);
  ">{badge}</div>

  <div style="
    flex:1 1 auto;
    font-size:18px;
    font-weight:500;
    line-height:1.35;
  ">{q["prompt"]}</div>
</div>
""",
        unsafe_allow_html=True
    )

    if st.session_state.get("quiz_type") == "meaning":
        tts_text = (q.get("reading") or q.get("jp_word") or "").strip()

        # ✅ PRO만 버튼 렌더링 (무료는 루프 안에서 아무것도 안 찍음)
        if is_pro():
            render_pronounce_button(
                tts_text,
                uid=f"{st.session_state.quiz_version}_{idx}",
                label="🔊 발음"
            )

    widget_key = f"q_{st.session_state.quiz_version}_{idx}"

    prev = st.session_state.answers[idx]
    default_index = None
    if prev is not None and prev in q["choices"]:
        default_index = q["choices"].index(prev)

    choice = st.radio(
        label="보기",
        options=q["choices"],
        index=default_index,
        key=widget_key,
        label_visibility="collapsed",
        on_change=mark_progress_dirty,
    )
    st.session_state.answers[idx] = choice

sync_answers_from_widgets()


# ============================================================
# ✅ 제출/채점
# ============================================================
quiz_len = len(st.session_state.quiz)

# ✅ "지금 선택된 값"을 세션에서 읽어서 all_answered 판단
selected_now = []
for idx, q in enumerate(st.session_state.quiz):
    widget_key = f"q_{st.session_state.quiz_version}_{idx}"
    selected_now.append(st.session_state.get(widget_key, None))

all_answered = (quiz_len > 0) and all(a is not None for a in selected_now)

if st.button(
    "✅ 제출하고 채점하기",
    disabled=not all_answered,
    type="primary",
    use_container_width=True,
    key="btn_submit",
):
    st.session_state.submitted = True
    st.session_state.session_stats_applied_this_attempt = False

    # ✅ 제출 시점에만 answers에 확정 반영
    st.session_state.answers = selected_now

    # ✅ 중복 카운트 방지
    if not st.session_state.get("_counted_today", False):
        add_done_count(int(st.session_state.get("quiz_len", 10)))
        st.session_state["_counted_today"] = True

if not all_answered:
    st.info("모든 문제에 답을 선택하면 제출 버튼이 활성화됩니다.")


# ============================================================
# ✅ 제출 후 화면
# ============================================================
if st.session_state.submitted:
    show_post_ui = (SHOW_POST_SUBMIT_UI == "Y") or is_admin()

    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()

    current_type = st.session_state.quiz_type
    current_pos_group = st.session_state.pos_group
    k_now = mastery_key()

    score = 0
    wrong_list = []

    for idx, q in enumerate(st.session_state.quiz):
        picked = st.session_state.answers[idx]
        correct = q["correct_text"]
        word_key = str(q.get("jp_word", "")).strip()

        if picked == correct:
            score += 1
            if word_key:
                st.session_state.mastered_words.setdefault(k_now, set()).add(word_key)
        else:
            wrong_list.append({
                "No": idx + 1,
                "문제": str(q.get("prompt", "")),
                "내 답": "" if picked is None else str(picked),
                "정답": str(correct),
                "단어": str(q.get("jp_word", "")).strip(),
                "읽기": str(q.get("reading", "")).strip(),
                "뜻": str(q.get("meaning", "")).strip(),
                "품사": current_pos_group,   # ✅ 그룹 저장
                "유형": current_type,
            })

    st.session_state.wrong_list = wrong_list

    st.success(f"점수: {score} / {quiz_len}")

    # ✅ FREE 제한 카운트 누적 (제출 1회 = quiz_len 소비)
    #    같은 제출 화면에서 rerun이 여러 번 나도 중복 누적되지 않도록 1회만 적용
    if "free_limit_applied_this_attempt" not in st.session_state:
        st.session_state.free_limit_applied_this_attempt = False

    if not st.session_state.free_limit_applied_this_attempt:
        add_free_used(quiz_len)  # 보통 10
        st.session_state.free_limit_applied_this_attempt = True

    ratio = score / quiz_len if quiz_len else 0

    if ratio == 1:
        sfx("perfect")
    elif ratio >= 0.7:
        sfx("wrong")
    else:
        sfx("wrong")

    if ratio == 1:
        st.balloons()
        st.success("🎉 완벽해요! 전부 정답입니다.")
    elif ratio >= 0.7:
        st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
    else:
        st.warning("💪 괜찮아요! 틀린 문제는 성장의 재료예요. 다시 한 번 도전해봐요.")

    sb_authed_local = get_authed_sb()
    if sb_authed_local is None:
        if show_post_ui:
            st.warning("DB 저장/조회용 토큰이 없습니다. 다시 로그인해 주세요.")
    else:
        if not st.session_state.saved_this_attempt:
            try:
                run_db(lambda: save_attempt_to_db(
                    sb_authed=sb_authed_local,
                    user_id=user_id,
                    user_email=user_email,
                    pos=current_pos_group,   # ✅ 그룹 저장
                    quiz_type=current_type,
                    quiz_len=quiz_len,
                    score=score,
                    wrong_list=wrong_list,
                ))
                st.session_state.saved_this_attempt = True
            except Exception as e:
                if show_post_ui:
                    st.warning("DB 저장에 실패했습니다. (테이블/컬럼/권한/RLS 정책 확인 필요)")
                    st.write(str(e))

        if not st.session_state.stats_saved_this_attempt:
            try:
                sync_answers_from_widgets()
                items = build_word_results_bulk_payload(
                    quiz=st.session_state.quiz,
                    answers=st.session_state.answers,
                    quiz_type=current_type,
                    pos=current_pos_group,  # ✅ 그룹 기준
                )
                if items:
                    run_db(lambda: sb_authed_local.rpc("record_word_results_bulk", {"p_items": items}).execute())
                st.session_state.stats_saved_this_attempt = True
            except Exception as e:
                if show_post_ui and is_admin():
                    st.error("❌ 단어 통계(bulk) 저장 실패 (RPC/정책 확인)")
                    st.exception(e)

        try:
            save_progress_to_db(sb_authed_local, user_id)
        except Exception:
            pass

    # ============================================================
    # ✅ 콤보 계산 (⚠️ 반드시 제출 후에만)
    # ============================================================
    correct_flags = []
    for idx, q in enumerate(st.session_state.quiz):
        picked = st.session_state.answers[idx]
        correct = q["correct_text"]
        correct_flags.append(picked == correct)

    max_combo = compute_max_combo(correct_flags)
    render_combo_celebration(max_combo)
    render_combo_small_badge()

    # ============================================================
    # ✅ 제출 후 화면 내부 "오답노트" 블록
    # ============================================================
    if st.session_state.wrong_list:
        st.subheader("❌ 오답 노트")

    def _s(v):
        return "" if v is None else str(v)

    def _esc(x: str) -> str:
        x = _s(x)
        return (x.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&#39;"))

    STYLE = """
<style>
.wrong-card{
  border: 1px solid rgba(120,120,120,0.25);
  border-radius: 16px;
  padding: 14px 14px;
  margin-bottom: 10px;
  background: rgba(255,255,255,0.02);
}
.wrong-top{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:12px;
  margin-bottom: 8px;
}
.wrong-left{ min-width:0; }
.wrong-title{
  font-weight: 900;
  font-size: 15px;
  margin-bottom: 4px;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
.wrong-sub{
  opacity: 0.8;
  font-size: 12px;
}
.tag{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(120,120,120,0.25);
  background: rgba(255,255,255,0.03);
  white-space: nowrap;
}
.ans-row{
  display:grid;
  grid-template-columns: 72px 1fr;
  gap:10px;
  margin-top:6px;
  font-size: 13px;
}
.ans-k{ opacity: 0.7; font-weight: 700; }
</style>
"""

    cards = []
    for w in st.session_state.wrong_list:
        no = _s(w.get("No"))
        qtext = _s(w.get("문제"))
        picked = _s(w.get("내 답"))
        correct = _s(w.get("정답"))
        word = _s(w.get("단어"))
        reading = _s(w.get("읽기"))
        meaning = _s(w.get("뜻"))
        mode = quiz_label_map.get(w.get("유형"), _s(w.get("유형")))
        pos_label = POS_LABEL_MAP.get(w.get("품사"), _s(w.get("품사")))

        card_html = f"""
<div class="jp">
  <div class="wrong-card">
    <div class="wrong-top">
      <div class="wrong-left">
        <div class="wrong-title">Q{_esc(no)}. {_esc(word)}</div>
        <div class="wrong-sub">{_esc(qtext)} · 품사: {_esc(pos_label)} · 유형: {_esc(mode)}</div>
      </div>
      <div class="tag">오답</div>
    </div>

    <div class="ans-row"><div class="ans-k">내 답</div><div>{_esc(picked)}</div></div>
    <div class="ans-row"><div class="ans-k">정답</div><div><b>{_esc(correct)}</b></div></div>
    <div class="ans-row"><div class="ans-k">발음</div><div>{_esc(reading)}</div></div>
    <div class="ans-row"><div class="ans-k">뜻</div><div>{_esc(meaning)}</div></div>
  </div>
</div>
"""
        cards.append(card_html)

    def _render_cards(card_list: list[str], max_height: int = 650):
        if not card_list:
            return
        html_block = "".join(card_list)
        h = 190 * len(card_list) + 10
        h = max(190, min(h, max_height))

        components.html(
            textwrap.dedent(f"""
{STYLE}
{html_block}
"""),
            height=h,
        )

    MAX_PREVIEW = 3
    preview_cards = cards[:MAX_PREVIEW]
    rest_cards = cards[MAX_PREVIEW:]

    _render_cards(preview_cards, max_height=650)

    if rest_cards:
        with st.expander(f"오답 더 보기 (+{len(rest_cards)}개)", expanded=False):
            _render_cards(rest_cards, max_height=900)
            

# ============================================================
# ✅ 제출 후 하단 액션 버튼 (오답 유무와 무관하게 항상 표시)
# ============================================================
if st.session_state.get("submitted", False):
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cA, cB = st.columns(2)
    with cA:
        locked = free_limit_reached()

        if locked:
            st.caption("🔒 오늘 무료 한도(30문항)를 모두 사용했어요.")

        if st.button(
            "✅ 다음 10문항 시작하기",
            type="primary",
            use_container_width=True,
            key="btn_next_10",
            disabled=locked
        ):
            if locked:
                st.stop()

            clear_question_widget_keys()

            st.session_state["_counted_today"] = False
            
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state.free_limit_applied_this_attempt = False
            mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    with cB:
        # 오답이 있을 때만 활성화(없으면 disabled)
        has_wrongs = bool(st.session_state.get("wrong_list"))
        pro_only_disabled = (not is_pro()) or (not has_wrongs)
        if st.button(
            "❌ 틀린 문제만 다시 풀기",
            use_container_width=True,
            disabled=pro_only_disabled,
            key="btn_retry_wrongs_bottom_global"
        ):
            clear_question_widget_keys()
            retry_quiz = build_quiz_from_wrongs(
                st.session_state.wrong_list,
                st.session_state.quiz_type,
                st.session_state.pos_group
            )
            start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    show_naver_talk = (SHOW_NAVER_TALK == "N") or is_admin()
    if show_naver_talk:
        render_naver_talk()


