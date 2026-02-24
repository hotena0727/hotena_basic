Stage1(인사말) + explain_kr 추가 + UI 변경
1) data/talk_situations.csv : explain_kr(필수) 컬럼 추가(50문항 전체 채움)
2) talk.py : explain_kr 컬럼이 있으면 정답 제출 후 '원포인트 해설' 표시(없으면 숨김)
3) 버튼 동작: 상단은 '정답 제출' 유지(제출 후 비활성). '다음 문제'는 최하단(말하기 완료 아래)에서만 노출
적용:
- /mount/src/hotena_basic/talk.py 덮어쓰기
- /mount/src/hotena_basic/data/talk_situations.csv 덮어쓰기
