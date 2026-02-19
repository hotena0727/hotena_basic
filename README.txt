[Hotena] 회화 페이지(파형 녹음 복구 + 보기 랜덤 변동 버그 수정) + 테마 톤 통일 패치

1) 회화 페이지 수정
- 보기(choices)가 라디오 클릭 때마다 랜덤으로 바뀌던 문제 해결:
  - qid별 choices를 session_state에 캐시하여 "세트 시작~끝"까지 고정
  - 라디오 key도 qid별로 분리하여 질문 간 충돌 방지
  - 제출 상태도 qid별로 관리

- 제출 후:
  - 정답 자동 TTS 1회 재생(브라우저 SpeechSynthesis)
  - 말풍선 UI(상대/내 선택/정답)
  - 파형 포함 녹음/재생(저장 없음)

2) 테마 통일(홈은 건드리지 않음)
- words.py / kanji.py / mypage.py / talk_impl.py에 theme_hotena 적용
- floating menu가 있는 home.py는 변경하지 않습니다.

적용:
- zip 안의 파일들을 프로젝트 루트에 '덮어쓰기/추가' 하세요.
  (talk_impl.py, theme_hotena.py는 새로 추가)
- 기존 talk.py가 있다면 이 zip의 talk.py로 덮어쓰기(Stub 방식 유지)

주의:
- 홈허브(home.py)는 수정하지 않아서 floating menu가 사라질 일이 없습니다.
