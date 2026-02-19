[Hotena] 회화 페이지 오류( _get_code_from_file ) + 보기 랜덤 변경 + 파형 녹음 복구 패치

왜 에러가 나나?
- Streamlit Cloud에서 간헐적으로 talk.py가 "로딩 단계"에서 실패하는 경우가 있습니다.
- 그래서 talk.py를 매우 작은 stub으로 유지하고, 실제 코드는 talk_impl.py로 분리합니다.

반영 내용
1) talk.py = SAFE STUB (항상 작게 유지)
2) talk_impl.py
   - 보기(choices) qid별 캐시: 라디오 클릭 rerun에도 보기 순서 고정
   - 라디오 key / submitted 상태를 qid별로 분리
   - 제출 직후 정답 자동 TTS 1회
   - 파형 포함 녹음/재생 UI(저장 없음)
   - theme_hotena.apply_theme()로 톤 통일(회화 페이지)

적용
- talk.py 덮어쓰기
- talk_impl.py 추가(또는 덮어쓰기)
- theme_hotena.py 추가(없으면)

리부트 후 회화 페이지에서:
- 보기 선택해도 보기 순서가 바뀌지 않아야 함
- 제출 후 정답 자동 TTS 1회 + 파형 녹음 영역이 보여야 함
