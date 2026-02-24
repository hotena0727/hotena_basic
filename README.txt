# Hotena 회화(인사말) 1차 패키지 (디버그 포함)

## 증상: '인사말 유형(sub)'이 안 뜰 때
1) 디버그(문제 발생 시 열기) 확장 펼치기
2) 컬럼에 'sub'가 있는지 확인
3) sub unique가 비어있으면 -> CSV가 옛 파일이거나, sub 값이 비어있음
4) CSV_PATH가 /data/... 인지 확인 후 그 위치에 CSV를 덮어쓰기

## 포함 파일
- talk.py (디버그 expander 포함)
- data/talk_situations.csv  (aisatsu 50문항, sub 포함)
