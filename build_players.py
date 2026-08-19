"""FBref 8종 스탯을 바르셀로나 선수-시즌 한 장으로 병합한다.

시즌마다 열 구성이 달라(구형 시즌엔 xG·수비 세부 지표가 없다) 종류별로 합친 뒤
(선수, 시즌) 키로 외부 조인한다. 없는 값은 그대로 결측으로 둔다 — 0으로 채우면
"기록이 없다"와 "0이었다"가 섞인다.

  python build_players.py
"""
import logging
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
FBREF = ROOT / "data" / "fbref"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
CLUB = "Barcelona"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("players")

# 종류별로 가져올 열. 접두사가 겹쳐 종류마다 이름을 정리해 붙인다.
PICK = {
    "standard": {
        "Playing Time_MP": "경기", "Playing Time_Starts": "선발",
        "Playing Time_Min": "출전분", "Playing Time_90s": "90분수",
        "Performance_Gls": "골", "Performance_Ast": "도움",
        "Performance_G-PK": "필드골", "Performance_PK": "PK골",
        "Performance_CrdY": "경고", "Performance_CrdR": "퇴장",
        "Per 90 Minutes_Gls": "골p90", "Per 90 Minutes_Ast": "도움p90",
        "Expected_xG": "xG", "Expected_npxG": "npxG", "Expected_xAG": "xAG",
        "Progression_PrgC": "전진운반", "Progression_PrgP": "전진패스",
    },
    "shooting": {
        "Standard_Sh": "슛", "Standard_SoT": "유효슛", "Standard_SoT%": "유효슛%",
        "Standard_Sh/90": "슛p90", "Standard_G/Sh": "슛당골", "Standard_Dist": "평균슛거리",
    },
    "passing": {
        "Total_Cmp": "패스성공", "Total_Att": "패스시도", "Total_Cmp%": "패스성공률",
        "Total_PrgDist": "패스전진거리", "Short_Cmp%": "짧은패스%",
        "Medium_Cmp%": "중거리패스%", "Long_Cmp%": "롱패스%",
        "KP": "키패스", "1/3": "파이널서드패스", "PPA": "박스내패스", "CrsPA": "박스크로스",
    },
    "gca": {
        "SCA_SCA": "슛유도", "SCA_SCA90": "슛유도p90",
        "GCA_GCA": "골유도", "GCA_GCA90": "골유도p90",
    },
    "defense": {
        "Tackles_Tkl": "태클", "Tackles_TklW": "태클성공",
        "Blocks_Blocks": "블록", "Int": "인터셉트", "Clr": "클리어", "Err": "실책",
    },
    "possession": {
        "Touches_Touches": "터치", "Touches_Att Pen": "상대박스터치",
        "Take-Ons_Att": "드리블시도", "Take-Ons_Succ": "드리블성공",
        "Take-Ons_Succ%": "드리블성공률",
        "Carries_Carries": "캐리", "Carries_PrgDist": "캐리전진거리",
        "Carries_Mis": "미스컨트롤", "Carries_Dis": "탈취당함",
    },
    "misc": {
        "Performance_Fls": "파울", "Performance_Fld": "피파울",
        "Performance_Off": "오프사이드", "Performance_Crs": "크로스",
        "Performance_PKwon": "PK획득",
    },
    "keepers": {
        "Performance_GA": "실점", "Performance_Saves": "선방",
        "Performance_Save%": "선방률", "Performance_CS": "클린시트",
        "Performance_CS%": "클린시트율",
    },
}

KEY = ["Player", "season"]
IDENT = ["Player", "Nation", "Pos", "Squad", "Age", "Born", "season"]


def load_stat(stat: str) -> pd.DataFrame:
    """한 종류의 전 시즌을 합치고 바르사 선수만 남긴다."""
    frames = []
    for f in sorted(FBREF.glob(f"{stat}_*.parquet")):
        df = pd.read_parquet(f)
        if "Squad" not in df.columns:
            continue
        df = df[df["Squad"] == CLUB]
        if df.empty:
            continue
        keep = {c: n for c, n in PICK[stat].items() if c in df.columns}
        cols = [c for c in IDENT if c in df.columns] + list(keep)
        frames.append(df[cols].rename(columns=keep))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    # 같은 시즌에 같은 이름이 두 줄 있으면(중복 표기) 첫 줄만 쓴다
    return out.drop_duplicates(subset=KEY, keep="first")


def main() -> None:
    base = load_stat("standard")
    log.info("standard — 바르사 선수-시즌 %d행", len(base))

    merged = base
    for stat in ["shooting", "passing", "gca", "defense", "possession", "misc", "keepers"]:
        part = load_stat(stat)
        if part.empty:
            log.warning("%s — 바르사 행 없음", stat)
            continue
        new_cols = [c for c in part.columns if c not in IDENT]
        merged = merged.merge(part[KEY + new_cols], on=KEY, how="left")
        log.info("%-11s — %2d열 결합 (누적 %d열)", stat, len(new_cols), merged.shape[1])

    # 숫자 열을 실제 숫자로. FBref는 쉼표가 섞인 문자열로 주는 경우가 있다.
    for c in merged.columns:
        if c in IDENT:
            continue
        merged[c] = pd.to_numeric(
            merged[c].astype(str).str.replace(",", "", regex=False), errors="coerce")

    # Age가 "27-045"(나이-일수) 형태인 시즌이 있어 앞자리만 취한다
    if "Age" in merged.columns:
        merged["Age"] = pd.to_numeric(
            base["Age"].astype(str).str.extract(r"^(\d+)")[0], errors="coerce")

    # FBref가 라리가 페이지에서 세부 패스·수비·점유 지표를 빈 셀로 내려주는 탓에
    # 전 시즌 통째로 비는 열이 생긴다. 그대로 두면 대시보드에 빈 칸만 남으므로 버린다.
    dead = [c for c in merged.columns if c not in IDENT and merged[c].isna().all()]
    if dead:
        log.info("전 시즌 결측이라 제외한 %d열 — %s", len(dead), ", ".join(dead))
        merged = merged.drop(columns=dead)

    merged["포지션군"] = merged["Pos"].fillna("").str[:2].replace({
        "GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"})
    merged = merged.sort_values(["season", "출전분"], ascending=[True, False])

    merged.to_parquet(OUT / "players.parquet", index=False)
    log.info("저장 — %d행 %d열 · %.1fKB", len(merged), merged.shape[1],
             (OUT / "players.parquet").stat().st_size / 1024)
    log.info("시즌 %d개 (%s ~ %s) · 선수 %d명",
             merged["season"].nunique(), merged["season"].min(),
             merged["season"].max(), merged["Player"].nunique())

    # FBref 라리가 standard 테이블에는 xG가 없다(2017/18 이후도 마찬가지).
    # 시즌마다 제공 지표가 달라, 열별로 값이 존재하는 시즌 수를 남겨 둔다.
    n_seasons = merged["season"].nunique()
    filled = merged.notna().groupby(merged["season"]).any().sum()
    thin = filled[filled < n_seasons].sort_values()
    log.info("전 시즌 제공 %d열 · 일부 시즌만 제공 %d열",
             int((filled == n_seasons).sum()), len(thin))
    if len(thin):
        log.info("일부만 제공 — %s",
                 ", ".join(f"{c}({n}시즌)" for c, n in thin.items()))


if __name__ == "__main__":
    main()
