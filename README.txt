Hotena 테마 톤 통일 패치

포함:
- theme_hotena.py (공통 CSS/카드/배지 스타일)
- home.py: page_title Hatena -> Hotena, 기존 CSS reset 제거, 공통 테마 주입
- words.py / kanji.py: 잘못 들어가 있던 'theme_hotena.apply_hotena_theme()' 문자열 제거 + 올바른 위치에서 호출
- talk.py / mypage.py: 공통 테마 적용(기능 로직은 건드리지 않음)

적용:
1) 이 zip의 파일들을 프로젝트 루트에 덮어쓰기
2) 실행 후, 모든 페이지에서 버튼/카드/배지/배경 톤이 통일됩니다.
