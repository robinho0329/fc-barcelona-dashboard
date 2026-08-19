# 인계 문서 — FC Barcelona 대시보드

작성 시점 기준 상태와, 이어서 작업할 때 알아야 할 것들.

## 한 줄 요약

Streamlit 멀티페이지 13개. football-data.co.uk(라리가 경기), FBref(선수·전 대회),
StatsBomb·Understat(이벤트), Transfermarkt(사진·감독) 다섯 소스를 직접 수집해
집계한다. 모든 수치는 원본에서 계산하며 어디까지 덮는지 페이지에 명시한다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py            # 기본 8501, 개발 중에는 8531을 썼다
```

`.claude/launch.json`(워크스페이스 루트)에 `barcelona` 항목이 있고 포트는 8531이다.
8520은 EPL 대시보드가 이미 쓰고 있어 피했다.

## 구조

```
app.py                     st.navigation 진입점. 페이지 등록만 한다
_lib.py                    공통 CSS·팔레트·데이터 로더·피치 도형·사진 매칭
views/                     페이지 13개
  club.py                  홈 — 33시즌 요약
  eras.py                  역사·시대 분석 (감독 기준 7시대)
  legends.py               레전드 TOP 10 (카드 선택 → 상세)
  managers.py              역대 감독 (카드 선택 → 상세 + 한 줄 평)
  clasico.py               엘클라시코 (역사 서술·갤러리·전적)
  players.py               선수 아카이브 (대회별 + 사진)
  advanced.py              선수 고급 기록 (90분당·레이더)
  shots.py                 xG·슈팅 맵
  passes.py                패스 맵
  seasons.py               시즌 기록 검색
  model.py                 AI 모델
  coverage.py              데이터 제공 범위
```

## 수집 스크립트 (실행 순서)

| 스크립트 | 하는 일 | 소요 |
|----------|---------|------|
| `build_data.py` | raw CSV → 시즌 지표·순위표·클라시코·전체 경기 | 즉시 |
| `crawl_fbref.py` | FBref 라리가 선수 스탯 8종 × 33시즌 (264건) | ~45분 |
| `build_players.py` | 위 8종을 바르사 선수-시즌 한 장으로 병합 | 즉시 |
| `crawl_allcomps.py` | FBref 클럽 전 대회 경기 + **대회별 선수 스탯** | ~7분 |
| `fetch_statsbomb.py` | StatsBomb 이벤트 531경기 | ~14분 |
| `fetch_understat.py` | Understat 슛 2014/15~2025/26 | ~15분 |
| `crawl_portraits.py` | TM 선수 증명사진 316장 | ~22분 |
| `crawl_managers.py` | TM 감독 이력 + 사진 | ~2분 |
| `build_managers.py` | 재임 기간 × 라리가 경기로 감독 성적 집계 | 즉시 |
| `crawl_masia.py` | 바르사 B팀 명단 (라 마시아 판별용) | ~4분 |
| `fetch_images.py` | 커먼즈 이미지 (레전드·클라시코·홈·시대) | 오래 걸림 |
| `apply_inbox.py` | `assets/_inbox/`에 넣은 사진을 자산으로 반영 | 즉시 |
| `train_model.py` | 경기 결과 예측 모델 학습 | 즉시 |

## 데이터 현황

| 산출물 | 규모 |
|--------|------|
| `data/processed/club_season.parquet` | 33시즌 |
| `data/processed/club_matches.parquet` | 1,251경기 |
| `data/processed/all_matches.parquet` | 라리가 전 구단 12,592경기 |
| `data/processed/players.parquet` | 886행 · 라리가 상세 |
| `data/fbref_allcomps_players/` | 3,443행 · 367명 · 대회별 |
| `data/fbref_allcomps/` | 1,716경기 (챔스 325 포함) |
| `data/statsbomb/` | 531경기 · 슛 13,140 · 패스 367,738 |
| `data/understat/shots.parquet` | 슛 11,508 |
| `data/processed/masia.json` | B팀 출신 339명 |
| `assets/portraits/` + `_thumb/` | 316장 |
| `assets/managers/` | 25장 |

## 반드시 알아야 할 함정

### 1. Streamlit 캐시 키에 파일 수정 시각을 넣어야 한다

`@st.cache_data`를 인자 없는 로더에 걸면, 수집 스크립트를 다시 돌려 파일이
바뀌어도 **옛 내용이 계속 나온다**. 실제로 세 번 당했다(스토이치코프 사진이
안 나옴, 감독 사진이 이니셜로 남음, 모델 `KeyError: 'auc_win'`).

`_lib.py`의 `load_parquet` / `load_json` / `b64` / `load_dir`를 쓸 것.
페이지에서 `@st.cache_data`로 파일을 직접 읽지 말 것.

### 2. 라리가 순위는 상대전적을 먼저 본다

승점 동률이면 **동률 팀 간 상대전적 → 상대전적 골득실 → 전체 골득실** 순이다.
골득실을 바로 적용하면 2006/07이 바르사 우승으로 잘못 나온다(실제로는 레알이
상대전적 우위). `build_data.py`의 `_head_to_head()`가 이걸 처리한다.
**바르사 리그 우승은 이 규칙으로 16회다.**

### 3. FBref가 라리가 세부 지표를 빈 값으로 준다

패스 성공률·태클·터치·드리블 등 28개 열이 응답 자체에서 비어 있다(2024/25도,
2017/18도 동일). 재시도로 해결되지 않는다. `build_players.py`가 전 시즌 결측
열을 자동 제외한다. 그 지표들은 StatsBomb 이벤트로 대체했다.

### 4. FBref 표 맨 아래 합계 행

`Squad Total` / `Opponent Total`이 선수 행에 섞인다. `crawl_allcomps.py`의
`TOTAL_ROWS`가 걸러낸다. 다른 FBref 표를 새로 파싱하면 같은 처리가 필요하다.

### 5. FBref standard 스탯의 URL 경로는 `stats`

`/comps/12/{season}/standard/...`가 아니라 `/comps/12/{season}/stats/...`다.
골키퍼 테이블 id는 단수형 `stats_keeper`. `crawl_fbref.py`의 `STAT_TYPES` 참고.

### 6. Understat은 requests에 데이터를 안 준다

평범한 HTTP 요청에는 `shotsData`가 빠진 HTML이 온다. 브라우저로 열어야
`window.shotsData`가 채워진다. `fetch_understat.py`가 undetected-chromedriver로
JS 변수를 직접 읽는다. 오래 돌리면 렌더러가 타임아웃을 내므로 40건마다
드라이버를 재시작한다.

### 7. 커먼즈 이미지 다운로드는 429가 잦다

`upload.wikimedia.org`가 IP 단위로 레이트리밋을 오래 건다. `fetch_images.py`는
요청 간 25초 + 429 시 75/180/360초 백오프를 쓴다. 그래도 실패하면 후보
파일명이 틀린 경우가 많으니 커먼즈 검색으로 실제 이름을 확인할 것.

### 8. 사진은 `assets/_inbox/`로 넣는다

사용자가 직접 고른 사진을 쓸 때는 `assets/_inbox/{key}.jpg`에 놓고
`python apply_inbox.py`를 실행한다. 키는 `apply_inbox.py`의 `TARGETS` 참고
(messi, cruyff, puyol, figo, sunyol …). 여러 페이지가 쓰는 인물은 양쪽에
복사되고 출처가 "사용자 제공"으로 기록된다.

## 알려진 한계 (페이지에도 명시돼 있음)

- **2004/05 원본 손실** — football-data 파일이 27경기에서 잘려 있다.
  그 시즌 엘클라시코 두 경기도 없다.
- **컵대회 미포함(일부 페이지)** — 홈·시대분석·엘클라시코·감독 성적은 라리가만
  집계한다. 클럽 공식 통산과 숫자가 다른 이유. 전 대회 데이터는 별도로 있다.
- **패스 맵은 2020/21까지** — 패스 좌표를 주는 무료 소스가 StatsBomb뿐이고
  라리가 공개 범위가 거기서 끝난다. Understat은 슛만 준다. FBref는 라리가
  이벤트가 없다. FotMob API는 토큰이 필요하다.
- **StatsBomb 출전 시간은 근사** — 교체 시각이 없어 마지막 등장 분을 썼다.
  90분당 지표는 대략적인 비교용이다.
- **감독 명단 보충** — TM 이력에 카를레스 레샥(2001/02)과 티토 빌라노바
  (2012/13)가 없어 `build_managers.py`의 `MISSING`에 직접 넣었다.
- **임시 감독 표시** — 원본에 역할 구분이 없어 `CARETAKERS`에 직접 적었다.
- **선수 사진 매칭 79%** — 1990년대 선수는 TM에 사진이 아예 없다.

## AI 모델에 대해

정확도로는 기준선을 **못 넘는다**. 바르사가 리그에서 70.5% 이기므로 "항상 승"만
찍어도 70.5%가 나오고 모델은 70.0%다. 로그손실도 기준선과 거의 같다.

다만 **판별력은 있다** — 승 확률 AUC 0.629, 상위 25% 실제 승률 83.3% vs
하위 25% 58.3%. 페이지에 이 한계를 그대로 써 뒀다. 정확도를 올리려고 경기 중
기록(슛·코너)을 피처에 넣으면 예측이 아니라 결과 되짚기가 되므로 하지 말 것.

## 남은 작업

1. **라 마시아 페이지** — 데이터(`masia.json` 339명)는 다 모았고 페이지만 없다.
   선수 아카이브와 이름으로 대조해 **시즌별 유스 출신 출전 시간 비중**을 그리면
   크루이프가 심은 구조가 과르디올라 시대에 정점을 찍고 이후 어떻게 변했는지가
   한 곡선으로 나온다. 이름 매칭은 `_lib._name_key()` 방식을 그대로 쓰면 된다.
2. **티키타카 지수** — StatsBomb 패스량·짧은패스 비율 + FBref 전 대회 점유율로
   시즌별 곡선. 2008~2012 정점과 이후 변화를 보여주는 게 목표.
3. **연계 네트워크** — StatsBomb `is_assist`와 Understat `player_assisted`로
   누가 누구에게 어시스트했는지. MSN·차비-이니에스타-메시 삼각형을 그릴 수 있다.
4. **감독별 전술 스타일** — 경기당 슛·코너·파울(2005/06~)과 StatsBomb 패스량·
   압박으로 감독 페이지에 성향 지표 추가.
5. **시대 이미지 2장** — 포스트 과르디올라·재건 칸이 캄 노우 사진으로 대체돼
   있다. 더 나은 장면을 찾거나 사용자에게 받을 것.

## 이미지 저작권

레전드·클라시코 일부 사진은 사용자가 직접 전달한 상업 스포츠 사진이다.
저장소가 public이라는 점은 사용자에게 알렸고, 개인 포트폴리오이므로 그대로
커밋하기로 결정했다. 커먼즈 사진은 저작자·라이선스를 각 페이지 하단에 표기한다.
