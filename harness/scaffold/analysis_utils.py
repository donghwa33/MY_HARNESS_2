"""데이터 분석 공용 함수 (MY_HARNESS scaffold). 제조·품질 데이터(Lot·웨이퍼·설비 이력)에 맞춘 함수 포함.

원칙
- 열 이름은 모두 인자로 받는다. 특정 데이터 구조를 가정하지 않는다.
- 처리하지 못한 값은 조용히 넘기지 않고 에러를 내거나 격리 결과로 돌려준다.
- 표는 save_table, 그림은 save_fig 로 outputs/ 아래에 저장해 문서에서 출처로 인용한다.
- pandas 2.x / 3.x 모두에서 동작하도록 작성했다.
"""
from __future__ import annotations

import os
import re
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TABLE_DIR = os.path.join("outputs", "tables")
FIG_DIR = os.path.join("outputs", "figures")


# ---------------------------------------------------------------------------
# 저장 도우미
# ---------------------------------------------------------------------------
def save_table(df: pd.DataFrame, name: str, index: bool = False) -> str:
    """outputs/tables/<name>.csv 로 저장하고 경로를 돌려준다."""
    os.makedirs(TABLE_DIR, exist_ok=True)
    path = os.path.join(TABLE_DIR, f"{name}.csv")
    df.to_csv(path, index=index, encoding="utf-8-sig")
    return path


def save_fig(fig, name: str, dpi: int = 120) -> str:
    """outputs/figures/<name>.png 로 저장하고 닫는다."""
    os.makedirs(FIG_DIR, exist_ok=True)
    path = os.path.join(FIG_DIR, f"{name}.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def setup_korean_font() -> str | None:
    """사용 가능한 한글 폰트를 찾아 설정한다. 없으면 None (그림 라벨은 영어 권장)."""
    from matplotlib import font_manager

    candidates = ["NanumGothic", "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", "AppleGothic"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return name
    return None


# ---------------------------------------------------------------------------
# 프로파일링
# ---------------------------------------------------------------------------
def profile(df: pd.DataFrame, name: str, key_cols: Sequence[str] | None = None, top_n: int = 20) -> str:
    """데이터프레임 요약을 markdown 문자열로 돌려준다 (분석·판단은 하지 않는다)."""
    lines = [f"## {name}", "", f"- 행 수: {len(df):,} / 열 수: {df.shape[1]}"]
    if key_cols:
        dup = int(df.duplicated(list(key_cols)).sum())
        lines.append(f"- 키 {list(key_cols)} 중복 행: {dup:,}")
    lines += ["", "| 열 | dtype | 결측 | 고유값 수 | 범위 또는 상위 값 |", "|---|---|---|---|---|"]
    for col in df.columns:
        s = df[col]
        n_null = int(s.isna().sum())
        n_uniq = int(s.nunique(dropna=True))
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            desc = f"min={s.min()} / max={s.max()} / mean={s.mean():.4g}" if s.notna().any() else "-"
        else:
            vc = s.astype("string").value_counts(dropna=True).head(top_n)
            desc = ", ".join(f"{k}({v})" for k, v in vc.items())
            if n_uniq > top_n:
                desc += f" … (+{n_uniq - top_n})"
        lines.append(f"| {col} | {s.dtype} | {n_null} | {n_uniq} | {desc} |")
    pats = date_format_census(df)
    if pats:
        lines += ["", "### 날짜로 보이는 열의 포맷 분포"]
        for col, counts in pats.items():
            lines.append(f"- {col}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return "\n".join(lines) + "\n"


_DATE_PATTERNS = {
    "YYYY-MM-DD": r"^\d{4}-\d{1,2}-\d{1,2}",
    "NN/NN/YYYY": r"^\d{1,2}/\d{1,2}/\d{4}",
    "YYYYMMDD": r"^\d{8}$",
    "YYYY/MM/DD": r"^\d{4}/\d{1,2}/\d{1,2}",
    "YYYY.MM.DD": r"^\d{4}\.\d{1,2}\.\d{1,2}",
}


def date_format_census(df: pd.DataFrame, min_share: float = 0.5) -> dict:
    """문자열 열 중 날짜처럼 보이는 열의 포맷별 개수를 센다."""
    out = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) and not col.lower().endswith(("date", "time", "day")):
            continue
        s = s.dropna().astype(str).str.strip()
        if s.empty:
            continue
        counts = {k: int(s.str.match(p).sum()) for k, p in _DATE_PATTERNS.items()}
        counts = {k: v for k, v in counts.items() if v}
        if counts and sum(counts.values()) / len(s) >= min_share:
            out[col] = counts
    return out


# ---------------------------------------------------------------------------
# 정제
# ---------------------------------------------------------------------------
def infer_slash_order(series: pd.Series) -> str:
    """NN/NN/YYYY 값들로 월/일 순서를 판정한다. 'MDY' | 'DMY' | 'ambiguous'."""
    s = series.dropna().astype(str).str.strip()
    m = s.str.extract(r"^(\d{1,2})/(\d{1,2})/\d{4}")
    m = m.dropna().astype(int)
    if m.empty:
        return "ambiguous"
    first_max, second_max = m[0].max(), m[1].max()
    if first_max <= 12 < second_max:
        return "MDY"
    if second_max <= 12 < first_max:
        return "DMY"
    return "ambiguous"


def parse_dates_strict(series: pd.Series, formats: Sequence[str]) -> pd.Series:
    """허용 포맷 목록으로만 파싱한다. 하나라도 실패하면 실패값 예시와 함께 ValueError."""
    raw = series.astype("string").str.strip()
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    remaining = raw.notna()
    for fmt in formats:
        if not remaining.any():
            break
        parsed = pd.to_datetime(raw[remaining], format=fmt, errors="coerce")
        ok = parsed.notna()
        result.loc[parsed.index[ok]] = parsed[ok].astype("datetime64[ns]")
        remaining.loc[parsed.index[ok]] = False
    if remaining.any():
        bad = raw[remaining].unique()[:10]
        raise ValueError(f"허용 포맷 {list(formats)} 으로 파싱 실패 {int(remaining.sum())}건, 예: {list(bad)}")
    return result


def normalize_categories(
    series: pd.Series, mapping: dict, case_insensitive: bool = True, strip: bool = True
) -> pd.Series:
    """명시적 매핑으로 범주 표기를 통일한다. 매핑에 없는 값이 있으면 ValueError."""
    s = series.astype("string")
    if strip:
        s = s.str.strip()
    keymap = {(k.lower() if case_insensitive else k): v for k, v in mapping.items()}
    keys = s.str.lower() if case_insensitive else s
    out = keys.map(keymap)
    unknown = s[s.notna() & out.isna()].unique()
    if len(unknown):
        raise ValueError(f"매핑에 없는 값: {list(unknown)[:20]}")
    return out.astype("string")


def dedupe_keep(
    df: pd.DataFrame, keys: Sequence[str], order_col: str, keep: str = "first"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """키 중복을 order_col 순서 기준으로 정리한다. (남긴 행, 제거한 행) 을 돌려준다."""
    if keep not in ("first", "last"):
        raise ValueError("keep 은 'first' 또는 'last'")
    ordered = df.sort_values(list(keys) + [order_col], kind="mergesort")
    dup_mask = ordered.duplicated(list(keys), keep=keep)
    return ordered[~dup_mask].sort_index(), ordered[dup_mask].sort_index()


def isolate_out_of_range(
    df: pd.DataFrame, col: str, low: float, high: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """범위를 벗어난 행을 격리한다. (정상 행, 격리 행)."""
    bad = ~df[col].between(low, high) | df[col].isna()
    return df[~bad], df[bad]


def join_report(
    left: pd.DataFrame, right: pd.DataFrame, on: Sequence[str] | str, how: str = "inner"
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """조인 결과, 오른쪽에 없어 빠진 왼쪽 키 목록, 손실 비율(키 기준) 을 돌려준다."""
    on = [on] if isinstance(on, str) else list(on)
    left_keys = left[on].drop_duplicates()
    right_keys = right[on].drop_duplicates()
    chk = left_keys.merge(right_keys, on=on, how="left", indicator=True)
    lost = chk[chk["_merge"] == "left_only"][on].reset_index(drop=True)
    ratio = len(lost) / len(left_keys) if len(left_keys) else 0.0
    merged = left.merge(right, on=on, how=how)
    return merged, lost, ratio


# ---------------------------------------------------------------------------
# 분석
# ---------------------------------------------------------------------------
def unit_level(
    df: pd.DataFrame, unit_col: str, value_col: str, carry_cols: Iterable[str] = ()
) -> pd.DataFrame:
    """단위(예: Lot) 평균으로 집계한다. carry_cols 는 단위 안에서 값이 하나여야 한다."""
    carry_cols = list(carry_cols)
    if carry_cols:
        n_var = df.groupby(unit_col)[carry_cols].nunique(dropna=False)
        bad = n_var[(n_var > 1).any(axis=1)]
        if not bad.empty:
            raise ValueError(f"단위 안에서 값이 여러 개인 요인이 있음: {bad.index.tolist()[:10]}")
    agg = {value_col: "mean", **{c: "first" for c in carry_cols}}
    return df.groupby(unit_col, as_index=False).agg(agg)


def daily_trend(
    df: pd.DataFrame, date_col: str, value_col: str, group_col: str | None = None, unit_col: str | None = None
) -> pd.DataFrame:
    """일별 평균과 단위 수. unit_col 을 주면 단위 평균을 먼저 낸 뒤 일별로 평균한다."""
    d = df.copy()
    d["_day"] = pd.to_datetime(d[date_col]).dt.normalize()
    keys = ["_day"] + ([group_col] if group_col else [])
    if unit_col:
        d = d.groupby(keys + [unit_col], as_index=False)[value_col].mean()
        out = d.groupby(keys).agg(mean=(value_col, "mean"), n_units=(unit_col, "nunique")).reset_index()
    else:
        out = d.groupby(keys).agg(mean=(value_col, "mean"), n=(value_col, "size")).reset_index()
    return out.rename(columns={"_day": "day"})


def plot_trend(trend: pd.DataFrame, events: Sequence[tuple] = (), group_col: str | None = None,
               title: str = "Daily trend", ylabel: str = "value"):
    """daily_trend 결과를 그리고 이벤트 세로선을 표시한다. fig 를 돌려준다."""
    fig, ax = plt.subplots(figsize=(10, 4))
    if group_col:
        for g, sub in trend.groupby(group_col):
            ax.plot(sub["day"], sub["mean"], marker="o", ms=3, label=str(g))
        ax.legend()
    else:
        ax.plot(trend["day"], trend["mean"], marker="o", ms=3)
    event_overlay(ax, events)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    return fig


def event_overlay(ax, events: Sequence[tuple]) -> None:
    """events: [(날짜, 라벨), ...] 를 세로 점선으로 표시한다."""
    for i, (when, label) in enumerate(events):
        x = pd.to_datetime(when)
        ax.axvline(x, linestyle="--", alpha=0.6, color=f"C{(i + 3) % 10}")
        ax.annotate(str(label), xy=(x, 1.0), xycoords=("data", "axes fraction"),
                    rotation=90, va="top", ha="right", fontsize=8)


def period_compare(df: pd.DataFrame, date_col: str, value_col: str, split_date,
                   unit_col: str | None = None) -> pd.DataFrame:
    """split_date 이전/이후(이후는 split_date 포함) 평균, 단위 수, 차이."""
    d = df.copy()
    d["_period"] = np.where(pd.to_datetime(d[date_col]) < pd.to_datetime(split_date), "before", "after")
    if unit_col:
        d = d.groupby(["_period", unit_col], as_index=False)[value_col].mean()
        out = d.groupby("_period").agg(mean=(value_col, "mean"), n_units=(unit_col, "nunique"))
    else:
        out = d.groupby("_period").agg(mean=(value_col, "mean"), n=(value_col, "size"))
    out = out.reindex(["before", "after"])
    out.loc["diff(after-before)", "mean"] = out.loc["after", "mean"] - out.loc["before", "mean"]
    return out.reset_index().rename(columns={"_period": "period"})


def stratify(
    df: pd.DataFrame,
    factors: Sequence[str],
    value_col: str,
    unit_col: str | None = None,
    baseline: float | None = None,
    small_n: int = 10,
) -> pd.DataFrame:
    """요인 교차 셀별 평균·중앙값·단위 수. baseline 을 주면 차이를 함께 계산한다."""
    factors = list(factors)
    d = unit_level(df, unit_col, value_col, factors) if unit_col else df
    count_col = unit_col if unit_col else value_col
    out = d.groupby(factors).agg(
        mean=(value_col, "mean"),
        median=(value_col, "median"),
        n=(count_col, "nunique" if unit_col else "size"),
    ).reset_index()
    if baseline is not None:
        out["diff_vs_baseline"] = out["mean"] - baseline
    out["small_sample"] = out["n"] < small_n
    return out


def crosstab_counts(df: pd.DataFrame, a: str, b: str, unit_col: str | None = None,
                    normalize: str | bool = False) -> pd.DataFrame:
    """두 요인의 교차 빈도표 (교란·쏠림 확인). unit_col 을 주면 단위 수로 센다."""
    d = df.drop_duplicates([unit_col, a, b]) if unit_col else df
    return pd.crosstab(d[a], d[b], margins=not normalize, normalize=normalize)


def naive_vs_stratified(df: pd.DataFrame, focus: str, other: str, value_col: str,
                        unit_col: str | None = None) -> dict:
    """focus 요인의 단순 비교 차이와, other 로 층화한 뒤의 층별 차이를 함께 돌려준다."""
    d = unit_level(df, unit_col, value_col, [focus, other]) if unit_col else df
    naive = d.groupby(focus)[value_col].mean()
    strat = d.groupby([other, focus])[value_col].mean().unstack(focus)
    return {"naive": naive, "stratified": strat}


def bootstrap_diff(a: Sequence[float], b: Sequence[float], n: int = 2000, seed: int = 0,
                   ci: float = 0.95) -> dict:
    """평균 차이(a-b)와 부트스트랩 신뢰구간. 단위(Lot) 수준 값으로 넣는다."""
    a = np.asarray(pd.Series(a).dropna(), dtype=float)
    b = np.asarray(pd.Series(b).dropna(), dtype=float)
    if len(a) == 0 or len(b) == 0:
        raise ValueError("빈 표본")
    rng = np.random.default_rng(seed)
    diffs = rng.choice(a, (n, len(a))).mean(1) - rng.choice(b, (n, len(b))).mean(1)
    lo, hi = np.quantile(diffs, [(1 - ci) / 2, 1 - (1 - ci) / 2])
    return {"diff": float(a.mean() - b.mean()), "ci_low": float(lo), "ci_high": float(hi),
            "n_a": int(len(a)), "n_b": int(len(b)), "ci": ci}


def radial_profile(
    df: pd.DataFrame, x_col: str, y_col: str, pass_col: str,
    group_col: str | None = None, n_bins: int = 5, center: tuple | None = None,
) -> pd.DataFrame:
    """다이 좌표로 웨이퍼 중심~가장자리 반경 구간별 통과율을 계산한다.

    center 를 주지 않으면 좌표의 (최솟값+최댓값)/2 를 중심으로 쓴다.
    반경은 최대 반경으로 정규화하고 n_bins 개 동일 폭 구간으로 나눈다 (0=중심, n_bins-1=가장자리).
    """
    d = df.copy()
    cx = (d[x_col].min() + d[x_col].max()) / 2 if center is None else center[0]
    cy = (d[y_col].min() + d[y_col].max()) / 2 if center is None else center[1]
    r = np.hypot(d[x_col] - cx, d[y_col] - cy)
    rmax = r.max() if r.max() > 0 else 1.0
    d["r_bin"] = np.minimum((r / rmax * n_bins).astype(int), n_bins - 1)
    keys = ([group_col] if group_col else []) + ["r_bin"]
    out = d.groupby(keys).agg(pass_rate=(pass_col, "mean"), n_die=(pass_col, "size")).reset_index()
    return out


def plot_radial(radial: pd.DataFrame, group_col: str | None = None, title: str = "Radial pass rate"):
    fig, ax = plt.subplots(figsize=(6, 4))
    if group_col:
        for g, sub in radial.groupby(group_col):
            ax.plot(sub["r_bin"], sub["pass_rate"], marker="o", label=str(g))
        ax.legend()
    else:
        ax.plot(radial["r_bin"], radial["pass_rate"], marker="o")
    ax.set_xlabel("radius bin (0=center → edge)")
    ax.set_ylabel("pass rate")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    return fig


def waterfall(components: Sequence[tuple], start_label: str = "before", start_value: float | None = None,
              title: str = "Contribution breakdown"):
    """components: [(라벨, 기여값), ...]. (표, fig) 를 돌려준다. 잔차는 호출 측에서 항목으로 넣는다."""
    rows, cum = [], (start_value or 0.0)
    if start_value is not None:
        rows.append({"item": start_label, "value": start_value, "cumulative": cum})
    for label, val in components:
        cum += val
        rows.append({"item": label, "value": val, "cumulative": cum})
    table = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = 0.0 if start_value is None else start_value
    if start_value is not None:
        ax.bar(start_label, start_value, color="gray")
    for label, val in components:
        ax.bar(label, val, bottom=bottom, color="C2" if val >= 0 else "C3")
        bottom += val
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    return table, fig


__all__ = [n for n in dir() if not n.startswith("_") and n not in {"annotations", "os", "re", "np", "pd", "plt", "matplotlib"}]
