"""Understat에서 바르셀로나 슛 데이터(좌표·xG)를 받는다.

StatsBomb 오픈데이터가 2020/21에서 끊겨 최근 시즌 슈팅 맵이 비었다.
Understat은 2014/15부터 현재까지 슛 하나하나의 좌표와 xG를 제공한다.

주의: understat.com은 평범한 requests 요청에는 데이터를 빼고 내려준다.
브라우저에서는 window.shotsData 로 들어오므로 undetected-chromedriver로 열어
JS 변수를 직접 읽는다.

  python fetch_understat.py              # 2014~2025 전 시즌
  python fetch_understat.py 2021 2025    # 연도 범위
"""
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from selenium.common.exceptions import WebDriverException

EPL = Path(r"D:\workspace\EPL project")
sys.path.insert(0, str(EPL))
from crawlers.base_agent import BaseCrawlerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "understat"
CACHE = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

TEAM = "Barcelona"
BASE = "https://understat.com"
PAGE_WAIT = 2.2  # JS가 변수를 채울 시간

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("understat")


class UnderstatAgent(BaseCrawlerAgent):
    """EPL 프로젝트의 드라이버 설정을 그대로 쓴다. 직접 만든 headless 드라이버는
    이 환경에서 기동에 실패해, 검증된 쪽을 재사용한다."""

    def __init__(self):
        super().__init__(source_name="understat", min_interval=1.0)


def restart(agent: BaseCrawlerAgent):
    """드라이버를 새로 띄운다. 수백 페이지를 열면 렌더러가 응답을 멈춘다."""
    try:
        agent.close()
    except Exception:  # noqa: BLE001
        pass
    return agent._get_driver()


def read_var(agent: BaseCrawlerAgent, url: str, var: str, tries: int = 3):
    """페이지를 열고 전역 JS 변수를 읽는다.

    오래 돌리면 크롬 렌더러가 타임아웃을 내므로, 예외가 나면 드라이버를
    다시 띄우고 이어서 시도한다.
    """
    for attempt in range(tries):
        try:
            drv = agent._get_driver()
            drv.get(url)
            for _ in range(6):
                time.sleep(PAGE_WAIT / 2)
                val = drv.execute_script(
                    f"return (typeof {var} !== 'undefined') ? {var} : null;")
                if val:
                    return val
        except WebDriverException as exc:
            log.info("      %s — %s, 드라이버 재시작", url.rsplit("/", 1)[-1],
                     type(exc).__name__)
            restart(agent)
            time.sleep(2)
            continue
        log.info("      %s — %s 없음, 재시도 %d", url.rsplit("/", 1)[-1], var, attempt + 1)
        time.sleep(3 * (attempt + 1))
    return None


def season_matches(agent, year: int) -> list[dict]:
    data = read_var(agent, f"{BASE}/team/{TEAM}/{year}", "datesData")
    return [m for m in (data or []) if m.get("isResult")]


def match_shots(agent, match_id: str) -> list[dict]:
    """한 경기의 슛 전량. 캐시가 있으면 네트워크를 건너뛴다."""
    cached = CACHE / f"{match_id}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    data = read_var(agent, f"{BASE}/match/{match_id}", "shotsData")
    if not data:
        return []
    shots = (data.get("h") or []) + (data.get("a") or [])
    cached.write_text(json.dumps(shots, ensure_ascii=False), encoding="utf-8")
    return shots


def main() -> None:
    years = range(2014, 2026)
    if len(sys.argv) == 3:
        years = range(int(sys.argv[1]), int(sys.argv[2]) + 1)

    agent = UnderstatAgent()
    rows: list[dict] = []
    t0 = time.time()
    try:
        for i, year in enumerate(years, 1):
            matches = season_matches(agent, year)
            if not matches:
                log.warning("%d — 경기 목록 없음", year)
                continue
            got = 0
            for j, m in enumerate(matches, 1):
                if j % 40 == 0:
                    restart(agent)
                shots = match_shots(agent, m["id"])
                if shots:
                    rows += shots
                    got += 1
            rate = (time.time() - t0) / i
            log.info("[%d/%d] %d/%02d — 경기 %d건 · 슛 누적 %d · 남은 %.0f분",
                     i, len(list(years)), year, (year + 1) % 100, got, len(rows),
                     rate * (len(list(years)) - i) / 60)
    finally:
        try:
            agent.close()
        except Exception:  # noqa: BLE001 — 종료 실패는 결과에 영향 없다
            pass

    if not rows:
        sys.exit("받은 슛이 없습니다.")

    df = pd.DataFrame(rows)
    # Understat 좌표는 0~1 비율이다. StatsBomb 좌표계(120x80)로 맞춰 두면
    # 기존 피치 그리기 코드를 그대로 쓸 수 있다.
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df["xG"] = pd.to_numeric(df["xG"], errors="coerce")
    df["minute"] = pd.to_numeric(df["minute"], errors="coerce")
    df["x"] = df["X"] * 120
    df["y"] = df["Y"] * 80

    df["is_barca"] = (((df["h_a"] == "h") & (df["h_team"] == TEAM))
                      | ((df["h_a"] == "a") & (df["a_team"] == TEAM)))
    df["team"] = df["h_team"].where(df["h_a"] == "h", df["a_team"])
    df["goal"] = df["result"] == "Goal"
    df["season"] = df["season"].astype(int).map(lambda y: f"{y}/{str(y + 1)[-2:]}")
    df = df.rename(columns={"player": "player_name", "xG": "xg",
                            "situation": "pattern", "shotType": "body_part",
                            "result": "outcome"})
    keep = ["match_id", "season", "date", "team", "is_barca", "player_name", "minute",
            "x", "y", "xg", "outcome", "goal", "body_part", "pattern",
            "player_assisted", "lastAction"]
    df[keep].to_parquet(OUT / "shots.parquet", index=False)

    b = df[df["is_barca"]]
    log.info("저장 — 슛 %d (바르사 %d) · 시즌 %d개 · %.1f분",
             len(df), len(b), df["season"].nunique(), (time.time() - t0) / 60)
    log.info("바르사 골 %d · 누적 xG %.1f", int(b["goal"].sum()), b["xg"].sum())


if __name__ == "__main__":
    main()
