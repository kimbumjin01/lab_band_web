# 🎸 LAB A팀 합주 관리

👉 **[snu-band-lab.streamlit.app](https://snu-band-lab.streamlit.app/)**

서울대학교 자연과학대학 밴드 **LAB** A팀을 위한 합주 관리 웹서비스입니다.  
선곡 투표, 일정 조정, 합주실 예약을 하나의 앱에서 처리합니다.

---

## 주요 기능

| 메뉴 | 설명 |
|------|------|
| 🎵 **선곡 투표** | 유튜브 링크로 곡 등록, 1~5점 투표, 댓글 의견 공유 |
| 📅 **일정 조정** | 드래그로 가능 시간 선택 · 팀 가용 인원 히트맵 확인 |
| 🎹 **합주실 예약** | 주요 합주실 예약 사이트 바로가기 |

### 세부 사항

- **인증** — 팀원별 개인 비밀번호로 로그인
- **팀장 전용** — 선곡 평균 점수 확인 · 합주 확정 일정 공지
- **확정 일정** — 메인 화면 상단에 다음 합주 일정 상시 표시
- **모바일 지원** — 터치 드래그 타임테이블

---

## 기술 스택

| | |
|---|---|
| Frontend & Backend | Python · Streamlit |
| Database | Supabase (PostgreSQL) |
| Custom Components | HTML / CSS / JavaScript |

---

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

`.streamlit/secrets.toml` 설정이 필요합니다. ([예시](.streamlit/secrets.toml.example) 참고)

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJ..."

[passwords]
"김범진" = "****"
# ...
```

---

## 프로젝트 구조

```
lab_band_web/
├── app.py
├── db.py
├── schedule_timetable/     # 드래그 타임테이블 컴포넌트
├── availability_table/     # 가용성 요약 테이블 컴포넌트
├── requirements.txt
└── README.md
```

---

*Developed by [@kbj110](https://github.com/kimbumjin01)*