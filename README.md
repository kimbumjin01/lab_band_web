# 🎸 LAB A팀 합주 관리 앱 (SNU Band Lab)

👉 **[서비스 바로가기](https://snu-band-lab.streamlit.app/)** — https://snu-band-lab.streamlit.app/

---

## 프로젝트 목적

서울대학교 자연과학대학 밴드 **LAB**의 A팀을 위한 체계적인 합주 관리 앱입니다. 팀원들이 모바일에서도 간편하게 접속하여 합주곡 추천/투표, When2Meet 스타일의 일정 조정, 합주실 예약 정보 확인을 빠르고 효율적으로 진행할 수 있도록 돕습니다.

## 사용 방법 (팀원용)

1. 위 링크로 접속합니다.
2. **상단에서 본인 이름**을 선택합니다. (이름을 고르기 전에는 선곡·일정 메뉴를 쓸 수 없습니다.)
3. 왼쪽 메뉴에서 원하는 기능을 선택합니다.

| 메뉴 | 하는 일 |
|------|---------|
| **선곡 투표** | 곡을 유튜브 링크와 함께 등록하고, 1~5점으로 투표합니다. |
| **일정 조정** | 손가락·마우스로 쓸어 가능한 시간을 고른 뒤 **저장하기**를 누릅니다. |
| **합주실 예약** | 합주실 예약 사이트로 바로 이동합니다. (이름 선택 없이 이용 가능) |

> **팀장(김범진)**만 비밀번호 인증 후 선곡 **평균 점수**를 확인할 수 있습니다.

## Technical Base

| 구분 | 기술 |
|------|------|
| **Frontend & Backend** | Python, Streamlit |
| **Database** | Supabase |
| **Custom UI** | HTML/JS/CSS (모바일 드래그 타임테이블 구현) |

---

## 개발자용 (로컬 실행)

```bash
pip install -r requirements.txt
streamlit run app.py
```

로컬 주소: http://localhost:8501

### Supabase 설정

`.streamlit/secrets.toml`에 아래 항목을 설정합니다. (예시: [secrets.toml.example](.streamlit/secrets.toml.example))

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJ..."
```

테이블 스키마는 Supabase SQL Editor에서 `songs`, `votes`, `availability` 테이블을 생성해 사용합니다.

### 프로젝트 구조

```
lab_band_web/
├── app.py
├── db.py
├── schedule_timetable/
├── requirements.txt
└── README.md
```

---

*Developed by LAB A Team @kbj110.*
