"""FBref 클럽 페이지에서 바르셀로나의 전 대회 경기를 받는다.

football-data.co.uk 원본은 라리가만 담고 있어 챔피언스리그·코파 델 레이가
빠져 있었다. FBref 클럽 시즌 페이지의 matchlogs_for 표에는 그 시즌 모든
대회 경기가 한 장에 들어 있고, 점유율·포메이션·주장까지 붙어 온다.

  python crawl_allcomps.py            # 전 시즌
  python crawl_allcomps.py 2015 2025  # 연도 범위
"""
import logging
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
OUT.mkdir(parents=True, exist_ok=True)

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


def parse(soup: BeautifulSoup) -> pd.DataFrame | None:
    t = find_table(soup, "matchlogs_for")
    if t is None:
        return None
    df = pd.read_html(StringIO(str(t)))[0]
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [b if str(a).startswith("Unnamed") else f"{a}_{b}"
                      for a, b in df.columns]
    # 표 중간에 반복되는 머리글 행을 걷어낸다
    df = df[df["Date"].notna() & (df["Date"] != "Date")]
    return df.reset_index(drop=True)


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
            if dest.exists():
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
