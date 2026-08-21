"""FBref 클럽 페이지에서 바르셀로나의 전 대회 경기를 받는다.

football-data.co.uk 원본은 라리가만 담고 있어 챔피언스리그·코파 델 레이가
빠져 있었다. FBref 클럽 시즌 페이지의 matchlogs_for 표에는 그 시즌 모든
대회 경기가 한 장에 들어 있고, 점유율·포메이션·주장까지 붙어 온다.

  python crawl_allcomps.py            # 전 시즌
  python crawl_allcomps.py 2015 2025  # 연도 범위
"""
import logging
import re
import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, Comment

EPL = Path(r"D:\workspace\EPL project")
sys.path.insert(0, str(EPL))
from crawlers.base_agent import BaseCrawlerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "fbref_allcomps"
PLAYERS_OUT = ROOT / "data" / "fbref_allcomps_players"
OUT.mkdir(parents=True, exist_ok=True)
PLAYERS_OUT.mkdir(parents=True, exist_ok=True)

SQUAD_ID = "206d90db"  # FBref의 바르셀로나 팀 id
URL = ("https://fbref.com/en/squads/{sid}/{season}/all_comps/"
       "Barcelona-Stats-All-Competitions")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("allcomps")


class FBrefAgent(BaseCrawlerAgent):
    def __init__(self):
        super().__init__(source_name="fbref", min_interval=6.0)


def find_table(soup: BeautifulSoup, tid: str):
    """FBref는 표를 HTML 주석 안에 숨겨 두기도 한다."""
    t = soup.find("table", id=tid)
    if t is not None:
        return t
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if tid in c:
            t = BeautifulSoup(c, "html.parser").find("table", id=tid)
            if t is not None:
                return t
    return None


def read_table(t) -> pd.DataFrame:
    df = pd.read_html(StringIO(str(t)))[0]
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [b if str(a).startswith("Unnamed") else f"{a}_{b}"
                      for a, b in df.columns]
    return df


def parse(soup: BeautifulSoup) -> pd.DataFrame | None:
    t = find_table(soup, "matchlogs_for")
    if t is None:
        return None
    df = read_table(t)
    # 표 중간에 반복되는 머리글 행을 걷어낸다
    df = df[df["Date"].notna() & (df["Date"] != "Date")]
    return df.reset_index(drop=True)


# FBref 대회 id → 표시명. 목록을 하드코딩하면 그해만 나오는 대회를 놓친다.
# 실제로 2015/16의 UEFA 슈퍼컵(id 122)이 빠져 '전 대회'가 대회 합보다 커졌다.
# 그래서 페이지에 있는 표를 전부 훑고, 이름은 아래 표로 옮기되 모르는 id는
# 그대로 남긴다.
# id 19는 UEFA 슈퍼컵이 아니라 유로파리그(옛 UEFA컵)다. 진짜 UEFA 슈퍼컵은
# id 122. 예전에 둘 다 "UEFA 슈퍼컵"으로 묶어 버려 경기 단위 'Comp'
# (UEFA Cup / Europa Lg)와 어긋났다(1995/96·2000/01·2003/04·2021/22·2022/23
# 시즌 선수 최대 출전 경기가 8~10인데 슈퍼컵은 단판이라 말이 안 됐음).
COMP_NAMES = {
    "combined": "전 대회", "12": "라리가", "8": "챔피언스리그",
    "569": "코파 델 레이", "646": "수페르코파", "14": "UEFA컵/유로파",
    "19": "UEFA컵/유로파", "122": "UEFA 슈퍼컵", "1": "클럽월드컵",
}
COMP_ID_RE = re.compile(r"^stats_standard_(.+)$")


def parse_players(soup: BeautifulSoup) -> pd.DataFrame | None:
    """대회별 + 전 대회 합산 선수 스탯을 한 표로 세로로 쌓는다.

    라리가만 담은 players.parquet과 달리 챔피언스리그·코파 델 레이까지 담는다.
    '대회' 열로 걸러 쓰면 되고, '전 대회'는 합산 행이라 다른 행과 더하면 중복이다.
    """
    # 주석 안에 숨은 표까지 포함해 stats_standard_* 를 모두 찾는다
    seen, tables = set(), []
    pools = [soup]
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if "stats_standard" in c:
            pools.append(BeautifulSoup(c, "html.parser"))
    for pool in pools:
        for t in pool.find_all("table"):
            tid = t.get("id", "")
            m = COMP_ID_RE.match(tid)
            if not m or tid in seen:
                continue
            seen.add(tid)
            tables.append((m.group(1), t))

    frames = []
    for key, t in tables:
        one = _shape_players(read_table(t))
        if one is None:
            continue
        one["대회"] = COMP_NAMES.get(key, f"기타({key})")
        frames.append(one)
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    # 같은 표시명이 여러 id로 잡히면(예: 슈퍼컵) 합쳐 준다
    keyed = ["Player", "season"] if "season" in out.columns else ["Player"]
    dup = out[out.duplicated(keyed + ["대회"], keep=False)]
    if len(dup):
        num = [c for c in out.columns if c not in ("Player", "Nation", "Pos", "대회")]
        out = (out.groupby(keyed + ["대회", "Nation", "Pos"], dropna=False)[num]
               .sum(min_count=1).reset_index())
    return out


# FBref 표 맨 아래에 붙는 팀 합계 행. 선수로 섞이면 '최다 득점 578골 Squad Total'
# 같은 엉뚱한 결과가 나온다.
TOTAL_ROWS = {"Squad Total", "Opponent Total"}


def _shape_players(df: pd.DataFrame) -> pd.DataFrame | None:
    df = df[df["Player"].notna() & (df["Player"] != "Player")]
    df = df[~df["Player"].isin(TOTAL_ROWS)]
    if df.empty:
        return None

    # FBref는 시즌에 따라 출전 경기 열을 'MP'로도, 'Playing Time_MP'로도 준다.
    # 한쪽만 잡으면 그 시즌 경기 수가 통째로 비어 '선발 > 경기' 같은 값이 나온다.
    if "MP" not in df.columns and "Playing Time_MP" in df.columns:
        df = df.rename(columns={"Playing Time_MP": "MP"})

    keep = {
        "Player": "Player", "Nation": "Nation", "Pos": "Pos", "Age": "Age",
        "MP": "경기", "Playing Time_Starts": "선발", "Playing Time_Min": "출전분",
        "Playing Time_90s": "90분수", "Performance_Gls": "골",
        "Performance_Ast": "도움", "Performance_G+A": "공격P",
        "Performance_G-PK": "필드골", "Performance_PK": "PK골",
        "Performance_CrdY": "경고", "Performance_CrdR": "퇴장",
        "Per 90 Minutes_Gls": "골p90", "Per 90 Minutes_Ast": "도움p90",
    }
    cols = {c: n for c, n in keep.items() if c in df.columns}
    out = df[list(cols)].rename(columns=cols)
    for c in out.columns:
        if c in ("Player", "Nation", "Pos"):
            continue
        out[c] = pd.to_numeric(
            out[c].astype(str).str.replace(",", "", regex=False).str.extract(r"^(\d+\.?\d*)")[0],
            errors="coerce")
    return out.reset_index(drop=True)


def main() -> None:
    years = range(1993, 2026)
    if len(sys.argv) == 3:
        years = range(int(sys.argv[1]), int(sys.argv[2]) + 1)
    years = list(years)

    agent = FBrefAgent()
    ok = skip = 0
    t0 = time.time()
    try:
        for i, y in enumerate(years, 1):
            season = f"{y}-{y + 1}"
            dest = OUT / f"{season}.parquet"
            pdest = PLAYERS_OUT / f"{season}.parquet"
            if dest.exists() and pdest.exists():
                skip += 1
                continue
            try:
                soup = agent.fetch(URL.format(sid=SQUAD_ID, season=season))
            except Exception as exc:  # noqa: BLE001 — 한 시즌 실패로 멈추지 않는다
                log.error("%s — %s: %s", season, type(exc).__name__, exc)
                continue
            if not soup:
                log.warning("%s — 응답 없음", season)
                continue
            df = parse(soup)
            if df is None or df.empty:
                log.info("[%d/%d] %s — 경기표 없음", i, len(years), season)
                continue
            df["season"] = f"{y}/{str(y + 1)[-2:]}"
            df.to_parquet(dest, index=False)

            pdf = parse_players(soup)
            if pdf is not None:
                pdf["season"] = f"{y}/{str(y + 1)[-2:]}"
                pdf.to_parquet(pdest, index=False)
            ok += 1
            comps = df["Comp"].dropna().unique().tolist() if "Comp" in df else []
            rate = (time.time() - t0) / i
            log.info("[%d/%d] %s — %d경기 · %s · 남은 %.0f분",
                     i, len(years), season, len(df), ", ".join(comps),
                     rate * (len(years) - i) / 60)
    finally:
        agent.close()

    log.info("완료 — 저장 %d · 건너뜀 %d · %.1f분", ok, skip, (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
