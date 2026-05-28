# LAB A팀 합주 관리

Streamlit 기반 밴드 합주 관리 웹앱입니다. 선곡 투표, 일정 조정, 합주실 예약 기능을 제공하며 데이터는 Supabase에 저장됩니다.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Supabase 설정

### 1. 테이블 생성

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

### 2. API 키 연결

`.streamlit/secrets.toml` 파일을 만들고 프로젝트 URL과 **anon public** 키를 입력합니다.

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJ..."
```

예시 파일: [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)

> `secrets.toml`은 Git에 올리지 마세요. Streamlit Cloud 배포 시에는 앱 설정 → Secrets에 동일한 키를 등록합니다.

## 프로젝트 구조

```
lab_band_web/
├── app.py              # Streamlit UI
├── db.py               # Supabase CRUD
├── .streamlit/
│   └── secrets.toml    # 로컬 비밀값 (gitignore)
├── requirements.txt
└── README.md
```
