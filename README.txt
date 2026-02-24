# Hotena 회화(인사말) 1차 패키지

## 포함 파일
- talk.py
- data/talk_situations.csv  (인사말 aisatsu 50문항, sub 컬럼 포함)

## 적용 방법 (Streamlit Cloud / Cloud Run 공통)
1) 서버의 /mount/src/hotena_basic/ 폴더에 talk.py를 덮어쓰기
2) 서버의 /mount/src/hotena_basic/data/ 폴더에 talk_situations.csv를 덮어쓰기
3) Streamlit 캐시가 남아있으면 앱 재시작(또는 Clear cache)

## 동작
- 상황 선택: 인사말(aisatsu)만
- 레벨 선택: 없음
- 인사말 유형(sub): CSV에 값이 있으면 자동 노출(전체/집/회사/전화/감사/사과 등)
