[Hotena] 회화 페이지 SyntaxError 응급 복구 패치

증상:
- home.py에서 run_script("talk.py") 호출 시, Streamlit Cloud에서 SyntaxError가 나며 talk.py 로딩 실패
- Traceback이 runpy._get_code_from_file에서 끝나는 형태

해결:
- talk.py를 아주 작은 "stub"로 교체(ASCII/UTF-8 안전)
- 실제 회화 코드는 talk_impl.py로 분리하여 실행

적용:
1) 이 zip을 풀면 talk.py, talk_impl.py 2개가 나옵니다.
2) 프로젝트 루트의 기존 talk.py를 이 talk.py로 "덮어쓰기"
3) talk_impl.py를 프로젝트 루트에 "추가"
4) 리부트

주의:
- 다른 파일은 건드리지 않습니다.
