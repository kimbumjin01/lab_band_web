# 🎸 LAB A팀 합주 관리 앱 (SNU Band Lab)

**[서비스 바로가기 → https://snu-band-lab.streamlit.app/](https://snu-band-lab.streamlit.app/)**

---

## 프로젝트 목적

서울대학교 자연과학대학 밴드 **LAB**의 A팀을 위한 체계적인 합주 관리 앱입니다. 팀원들이 모바일에서도 간편하게 접속하여 합주곡 추천/투표, When2Meet 스타일의 일정 조정, 합주실 예약 정보 확인을 빠르고 효율적으로 진행할 수 있도록 돕습니다.

## 주요 기능

| 메뉴 | 설명 |
|------|------|
| **선곡 투표** | 유튜브 링크와 함께 곡 등록, 팀원별 1~5점 투표 (팀장 인증 시 평균 점수 공개) |
| **일정 조정** | 드래그·터치 기반 가능 시간 선택, 팀 가능 인원 요약 표 |
| **합주실 예약** | 주요 합주실 예약 페이지 바로가기 (로그인 없이 이용 가능) |

## Technical Base

| 구분 | 기술 |
|------|------|
| **Frontend & Backend** | Python, Streamlit |
| **Database** | Supabase |
| **Custom UI** | HTML / JS / CSS (모바일 드래그 타임테이블 구현) |

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## Supabase 설정

### 테이블 생성

Supabase SQL Editor에서 아래 스키마를 실행합니다.

```sql
CREATE TABLE songs (
  id bigint primary key generated always as identity,
  title text not null,
  youtube_url text not null,
  uploaded_by text not null,
  created_at timestamptz default now()
);

CREATE TABLE votes (
  song_id bigint references songs(id) on delete cascade,
  member text not null,
  score smallint check (score between 1 and 5),
  primary key (song_id, member)
);

CREATE TABLE availability (
  member text not null,
  slot_date date not null,
  slot_time text not null,
  available boolean default false,
  primary key (member, slot_date, slot_time)
);
```

### API 키 연결

`.streamlit/secrets.toml` 파일을 만들고 프로젝트 URL과 **anon public** 키를 입력합니다.

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJ..."
```

예시: [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)

> `secrets.toml`은 Git에 올리지 마세요. [Streamlit Cloud](https://snu-band-lab.streamlit.app/) 배포 시 앱 설정 → **Secrets**에 동일한 키를 등록합니다.

## 프로젝트 구조

```
lab_band_web/
├── app.py                      # Streamlit 메인 UI
├── db.py                       # Supabase CRUD
├── schedule_timetable/         # 드래그 일정 커스텀 컴포넌트
│   └── frontend/index.html
├── .streamlit/
│   └── secrets.toml            # 로컬 비밀값 (gitignore)
├── requirements.txt
└── README.md
```

---

*Developed by LAB A Team Leader kbj110.*
