# 키즐링 박람회 리드 후속 이메일 자동화

## 대시보드 실행 방법

`scripts/build_dashboard.py`는 **Streamlit 앱이 아닌, 정적 HTML을 생성하는 일반 파이썬 스크립트**입니다.
`streamlit run`으로 실행하면 안 되고, 아래와 같이 실행합니다.

```bash
# 1) 가상환경 생성 (최초 1회)
python -m venv .venv

# 2) 패키지 설치 (최초 1회)
.venv/Scripts/pip install -r requirements.txt

# 3) 대시보드 생성
.venv/Scripts/python.exe scripts/build_dashboard.py
```

실행하면 `output/dashboard.html`이 생성/갱신됩니다. 이 파일을 더블클릭해 브라우저로 열면 됩니다(별도 서버 불필요).

리드 CSV(`data/leads_sample.csv`, `data/leads_dummy_100_test.csv`)나 이메일 초안 CSV(`output/email_drafts.csv`, `output/email_drafts_test.csv`)를 갱신한 뒤 스크립트를 다시 실행하면 대시보드도 그대로 갱신됩니다.

## 대시보드 내용

- Basic 제출물(50건) / 재현성 테스트(100건) 탭 비교
- 직책·관심제품(interest_feature)·follow_up_priority 분포 차트
- 직책 × 우선순위 매트릭스
- 직책·우선순위·review_flag·검색어로 필터링 가능한 리드별 이메일 초안 테이블
