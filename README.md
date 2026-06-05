# LAB A팀 합주 관리

[snu-band-lab.streamlit.app](https://snu-band-lab.streamlit.app/)

서울대학교 자연과학대학 밴드 **LAB A팀**의 합주 운영을 돕는 Streamlit 기반 웹 애플리케이션입니다. 선곡 투표, 팀원별 가능 시간 수집, 합주 일정 확정, 합주실 예약 링크를 하나의 화면 흐름 안에서 관리합니다.

## 주요 기능

| 영역 | 기능 |
| --- | --- |
| 선곡 투표 | 유튜브 링크 기반 곡 등록, 1-5점 투표, 곡별 의견 작성 |
| 일정 조정 | 드래그 가능한 타임테이블, 개인 가능 시간 저장, 팀 가용 인원 히트맵 |
| 팀장 기능 | 선곡 평균 점수 확인, 확정 합주 일정 등록 및 삭제 |
| 합주실 예약 | 자주 쓰는 합주실 예약 페이지 바로가기 |
| 인증 | 팀원 이름과 개인 비밀번호 기반의 간단한 접근 제어 |

## 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| App | Python, Streamlit |
| Database | Supabase PostgreSQL |
| UI Component | Streamlit Custom Components, HTML, CSS, JavaScript |
| Data Handling | Streamlit cache, Supabase REST client |

## 구조

```text
lab_band_web/
├── app.py                         # Streamlit 앱 진입점과 화면 렌더링
├── db.py                          # Supabase 접근 함수
├── availability_table/            # 팀 가능 인원 요약 컴포넌트
│   └── frontend/
│       ├── index.html
│       └── index.template.html
├── schedule_timetable/            # 개인 일정 드래그 입력 컴포넌트
│   └── frontend/
│       ├── index.html
│       └── index.template.html
├── requirements.txt
└── README.md
```

## 데이터 모델

앱은 아래 Supabase 테이블을 사용합니다.

| 테이블 | 용도 | 주요 컬럼 |
| --- | --- | --- |
| `songs` | 후보곡 목록 | `id`, `title`, `youtube_url`, `uploaded_by`, `notes`, `created_at` |
| `votes` | 팀원별 곡 점수 | `song_id`, `member`, `score` |
| `song_comments` | 곡별 의견 | `id`, `song_id`, `member`, `content`, `created_at` |
| `availability` | 팀원별 가능 시간 | `member`, `slot_date`, `slot_time`, `available` |
| `confirmed_schedules` | 확정 합주 일정 | `id`, `schedule_date`, `start_time`, `end_time`, `note`, `created_at` |

`upsert`가 정상 동작하려면 Supabase에서 다음 유니크 제약을 두는 것이 좋습니다.

```sql
create unique index if not exists votes_song_member_idx
on votes (song_id, member);

create unique index if not exists availability_member_slot_idx
on availability (member, slot_date, slot_time);
```

## 성능 설계

무료 Streamlit/Supabase 환경을 고려해 DB 호출과 rerun 비용을 줄이는 방향으로 구성했습니다.

- 곡, 투표, 댓글, 일정 데이터는 `st.cache_data`로 짧게 캐싱합니다.
- 선곡 화면은 페이지네이션을 적용해 한 번에 렌더링하는 곡 수를 제한합니다.
- 일정 입력은 셀 클릭마다 DB에 쓰지 않고, 사용자가 `저장하기`를 눌렀을 때 변경된 슬롯만 batch upsert합니다.
- 커스텀 컴포넌트는 Streamlit 인자로 데이터를 전달해 불필요한 런타임 파일 쓰기를 피합니다.
- Supabase 클라이언트는 `st.cache_resource`로 재사용합니다.

## 로컬 실행

Python 3.10 이상을 권장합니다.

```bash
pip install -r requirements.txt
streamlit run app.py
```

로컬 실행 전 `.streamlit/secrets.toml`을 생성해야 합니다. 예시는 [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example)을 참고하세요.

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJ..."

[passwords]
"김범진" = "your-password"
"팀원명" = "your-password"
```

## 운영 메모

- 팀원 목록, 팀장 계정, 팀 인원 기준은 [app.py](app.py)의 `MEMBER_OPTIONS`, `TEAM_LEADER`, `TEAM_SIZE`에서 관리합니다.
- Streamlit은 사용자 입력마다 앱을 rerun하므로 DB 쓰기는 반드시 버튼이나 form submit 뒤에 묶는 것이 좋습니다.
- Supabase 무료 플랜에서는 불필요한 전체 테이블 조회를 피하고, 데이터가 늘어나면 곡 목록과 댓글/투표 조회를 페이지 단위로 좁히는 것이 좋습니다.
- 비밀번호는 현재 Streamlit secrets에 저장하는 간단한 방식입니다. 외부 공개 범위가 넓어지면 Supabase Auth 또는 해시 기반 검증으로 전환하는 것을 권장합니다.

## Maintainer

Developed by [@kbj110](https://github.com/kimbumjin01)
