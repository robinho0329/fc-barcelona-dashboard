"""FBref 라리가 선수 시즌 스탯 크롤러.

시즌 전체 선수 스탯은 리그 페이지 한 장에 다 들어 있어 요청이 시즌×스탯종류로 끝난다.
EPL 프로젝트의 BaseCrawlerAgent(undetected-chromedriver + 레이트 리밋)를 재사용한다.

  python crawl_fbref.py            # 전 시즌 · 전 스탯 종류
  python crawl_fbref.py standard   # 특정 종류만
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
OUT = ROOT / "data" / "fbref"
OUT.mkdir(parents=True, exist_ok=True)

LALIGA_COMP = 12
BASE = "https://fbref.com"

# 스탯 종류 -> (URL 경로, 테이블 id 접두사).
# standard는 경로가 "stats"이고, 골키퍼 테이블 id는 단수형 "stats_keeper"다.
# 구형 시즌에는 없는 종류가 있어, 테이블이 없으면 건너뛴다.
STAT_TYPES = {
    "standard": ("stats", "stats_standard"),
    "shooting": ("shooting", "stats_shooting"),
    "passing": ("passing", "stats_passing"),
    "gca": ("gca", "stats_gca"),
    "defense": ("defense", "stats_defense"),
    "possession": ("possession", "stats_possession"),
    "misc": ("misc", "stats_misc"),
    "keepers": ("keepers", "stats_keeper"),
}

SEASONS = [f"{y}-{y + 1}" for y in range(1993, 2026)]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("fbref-laliga")


class LaLigaAgent(BaseCrawlerAgent):
    def __init__(self):
        super().__init__(source_name="fbref", min_interval=6.0)


def extract_table(soup: BeautifulSoup, prefix: str) -> pd.DataFrame | None:
    """id가 prefix로 시작하는 선수 테이블을 찾는다. FBref는 주석 안에 숨기기도 한다."""
    candidates = [t for t in soup.find_all("table")
                  if t.get("id", "").startswith(prefix)]
    if not candidates:
        for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
            if prefix not in c:
                continue
            candidates += [t for t in BeautifulSoup(c, "html.parser").find_all("table")
                           if t.get("id", "").startswith(prefix)]
    if not candidates:
        return None

    df = pd.read_html(StringIO(str(candidates[0])))[0]
    if isinstance(df.columns, pd.MultiIndex):
        # ('Unnamed: 0_level_0', 'Rk') 같은 상위 레벨은 버리고 하위만 쓴다
        df.columns = [b if str(a).startswith("Unnamed") else f"{a}_{b}"
                      for a, b in df.columns]
    df = df[df["Player"].notna() & (df["Player"] != "Player")]
    return df.reset_index(drop=True)


def main() -> None:
    types = sys.argv[1:] or list(STAT_TYPES)
    unknown = [t for t in types if t not in STAT_TYPES]
    if unknown:
        sys.exit(f"알 수 없는 스탯 종류: {unknown} (가능: {list(STAT_TYPES)})")
    agent = LaLigaAgent()
    todo = [(s, t) for s in SEASONS for t in types
            if not (OUT / f"{t}_{s}.parquet").exists()]
    log.info("대상 %d건 (시즌 %d × 종류 %d), 이미 받은 건 건너뜀",
             len(todo), len(SEASONS), len(types))

    ok = skip = fail = 0
    t0 = time.time()
    for i, (season, stat) in enumerate(todo, 1):
        path, table_prefix = STAT_TYPES[stat]
        url = f"{BASE}/en/comps/{LALIGA_COMP}/{season}/{path}/{season}-La-Liga-Stats"
        try:
            soup = agent.fetch(url)
            if not soup:
                log.warning("[%d/%d] %s %s — 응답 없음", i, len(todo), season, stat)
                fail += 1
                continue
            df = extract_table(soup, table_prefix)
            if df is None or df.empty:
                log.info("[%d/%d] %s %s — 테이블 없음(구형 시즌)", i, len(todo), season, stat)
                skip += 1
                continue
            df["season"] = f"{season[:4]}/{season[-2:]}"
            df.to_parquet(OUT / f"{stat}_{season}.parquet", index=False)
            ok += 1
            rate = (time.time() - t0) / i
            log.info("[%d/%d] %s %s — %d명 %d열 · 평균 %.1fs/건 · 남은 %.0f분",
                     i, len(todo), season, stat, len(df), df.shape[1],
                     rate, rate * (len(todo) - i) / 60)
        except Exception as exc:  # noqa: BLE001 — 한 건 실패로 전체를 멈추지 않는다
            log.error("[%d/%d] %s %s — %s: %s", i, len(todo), season, stat,
                      type(exc).__name__, exc)
            fail += 1

    log.info("완료 — 저장 %d · 미제공 %d · 실패 %d · 총 %.1f분",
             ok, skip, fail, (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
