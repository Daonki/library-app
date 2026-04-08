# 📚 도서관 찾자 (Library Finder)

전국 공공도서관 열람실 실시간 잔여석 조회 및 AI 맞춤 추천 웹 서비스

🔗 **배포 URL**: [https://library-findja.streamlit.app](https://library-findja.streamlit.app)

---

## 📌 서비스 소개

도서관 이용자들은 자리가 있는지 확인하기 위해 직접 방문하거나 각 도서관 홈페이지를 개별로 확인해야 하는 불편함이 있었습니다.  
**도서관 찾자**는 전국 120개 공공도서관의 실시간 잔여석을 한 곳에서 조회하고, GPT-4o-mini AI 모델로 맞춤 추천까지 제공합니다.

---

## ✨ 주요 기능

| 탭 | 기능 | 설명 |
|---|---|---|
| 🗺️ 지도 | 실시간 혼잡도 지도 | 전국 도서관 마커 표시 · 혼잡도 색상 구분 · 마커 클릭 상세 정보 |
| 📋 목록 | 도서관 목록 조회 | 📍 내 주변 도서관 찾기 · 이름 검색 · 지역/혼잡도/운영상태 필터 · 잔여석 정렬 |
| 📊 통계 | 지역별 통계 시각화 | 시간대별 혼잡도 예측 · AI 현황 리포트 · 지역별 사용률 차트 |
| 💬 AI 추천 | GPT-4o-mini 기반 AI | 자연어 질의응답 · 목적별 추천 · 운영시간 계산 · 도서관 비교 |

### 핵심 기술 특징
- **실시간 데이터**: 공공데이터포털 API를 통해 5분마다 자동 갱신
- **데이터 신선도**: 열람실별 마지막 업데이트 시각을 'N분 전' 형태로 표시
- **위치 기반 추천**: Geolocation API로 현재 위치에서 가까운 운영중 도서관 TOP 5 표시
- **혼잡도 변화 감지**: 5분 갱신 시 이전 데이터와 비교하여 혼잡도 변화 도서관 자동 알림
- **AI 통합**: GPT-4o-mini 기반 대화형 추천으로 자연어 질의응답 지원

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| 언어 / 프레임워크 | Python · Streamlit |
| 지도 시각화 | Folium · streamlit-folium · OpenStreetMap |
| 데이터 처리 | Pandas · Requests |
| 차트 시각화 | Plotly Express |
| AI / LLM | OpenAI GPT-4o-mini API |
| 위치 기반 | Geolocation API · streamlit-js-eval |
| 데이터 소스 | 공공데이터포털 공공도서관 API 3종 |
| 배포 환경 | Streamlit Cloud (GitHub 연동 자동 배포) |

---

## 📂 활용 공공데이터

| API명 | 제공기관 | 활용 내용 |
|---|---|---|
| 공공도서관 기본정보 (info_v2) | 국립중앙도서관 | 도서관명, 위치, 운영시간, 연락처 등 |
| 열람실 실시간 잔여석 (rlt_rdrm_info_v2) | 국립중앙도서관 | 열람실별 실시간 잔여석, 총좌석, 업데이트 시각 |
| 도서관 운영현황 (prst_info_v2) | 국립중앙도서관 | 운영중/휴관 여부, 오늘 방문자 수, 좌석 사용률 |

---

## 🚀 로컬 실행 방법

```bash
# 1. 레포지토리 클론
git clone https://github.com/Daonki/library-app.git
cd library-app

# 2. 패키지 설치
pip install -r requirements.txt

# 3. API 키 설정 (.streamlit/secrets.toml)
# OPENAI_API_KEY = "sk-..."
# KAKAO_JS_KEY = "..."

# 4. 실행
streamlit run app.py
```

---

## 📁 프로젝트 구조

```
library-app/
├── app.py          # 메인 Streamlit 앱
├── api.py          # 공공데이터 API 호출 모듈
├── ai.py           # GPT AI 추천 모듈
├── requirements.txt
└── .streamlit/
    └── secrets.toml  # API 키 (로컬용, Git 제외)
```

---

## 📝 개발 정보

- **개발 기간**: 2026년 4월
- **공모전**: 2026 전국 통합데이터 활용 공모전
