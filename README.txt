# Hatena Hub (단어/한자/회화)

실행:
  streamlit run home.py

필수 secrets/env:
  SUPABASE_URL
  SUPABASE_ANON_KEY
  COOKIE_PASSWORD

회화 CSV:
  data/talk_situations.csv


권장:
  - home.py만 실행(엔트리포인트)
  - 하위 페이지(app.py / hotena_basic.py / talk.py / mypage.py) 직접 실행은 비권장
