# FC Barcelona — Més que un club

라리가 33시즌(1993/94~2025/26) 바르셀로나 기록을 정리한 Streamlit 단일 페이지.
바이에른 뮌헨 페이지와 같은 레이아웃을 그라나(#a50044)·블라우(#004d98)·골드(#edbb00)로 옮겼다.

## 구조

```
barcelona/
├── app.py                       # Streamlit 앱 (단일 페이지)
├── build_data.py                # 원본 CSV → 시즌 지표 집계
├── requirements.txt
├── assets/                      # 엠블럼 + 사진 + 출처 메타
└── data/
    ├── raw/SP1_*.csv            # football-data.co.uk 라리가 원본 33시즌
    └── processed/               # 집계 결과 (parquet)
        ├── league_table.parquet  # 시즌별 전 구단 순위표
        ├── club_season.parquet   # 바르사 시즌 지표
        ├── club_matches.parquet  # 바르사 전 경기
        └── clasico.parquet       # 엘클라시코 (바르사 기준 정규화·날짜순)
```

## 실행

```bash
pip install -r requirements.txt
python build_data.py     # data/processed/ 생성
streamlit run app.py
```

## 데이터

- 출처: [football-data.co.uk](https://www.football-data.co.uk/spainm.php) 라리가 1부(SP1)
- 범위: 1993/94~2025/26 · 리그 1,251경기
- 순위는 원본에 없어 **승점 → 골득실 → 다득점** 순으로 직접 산출한다.
  상대전적을 우선하는 라리가 공식 규정과 일부 시즌에서 어긋날 수 있다.
- `build_data.py`가 리그 전체 경기로 시즌별 순위표를 만든 뒤 바르사 행만 추출한다.

## 집계 결과

| 항목 | 값 |
|------|-----|
| 분석 시즌 | 33 |
| 리그 경기 | 1,251 |
| 리그 우승 | 17회 |
| 총 득점 | 2,855 (경기당 2.28) |
| 통산 전적 | 813승 239무 199패 (승률 65.0%) |
| 최고 승점률 | 2.63 (2012/13, 승점 100) |
| 최다 득점 시즌 | 116골 (2016/17) |

### 엘클라시코 (리그 한정)

| 항목 | 값 |
|------|-----|
| 맞대결 | 64경기 (32시즌) |
| 전적 | 30승 14무 20패 (승률 47%) |
| 득실 | 119-86 (경기당 1.86 : 1.34) |
| 홈 / 원정 승리 | 16 / 14 |
| 최다 점수차 승 | 1993/94 홈 5-0, 2010/11 홈 5-0 |
| 최다 점수차 패 | 1994/95 원정 0-5 |

컵대회·챔피언스리그 맞대결은 원본에 없어 빠진다.
원본 파일이 잘려 있는 2004/05 두 경기도 제외된다.

## 이미지

엠블럼은 FC Barcelona 소유. 사진은 모두 Wikimedia Commons에서 받았으며
라이선스와 저작자는 `assets/credits.json`과 페이지 하단에 표기한다.

| 파일 | 저작자 | 라이선스 |
|------|--------|----------|
| camp_nou.jpg | Luis Miguel Bugallo Sánchez | CC BY-SA 3.0 |
| cruyff.jpg | Rob Mieremet / Anefo | CC0 |
| messi.jpg | Кирилл Венедиктов | CC BY-SA 3.0 |
