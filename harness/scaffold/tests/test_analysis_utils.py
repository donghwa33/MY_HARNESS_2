"""스캐폴드 자체 테스트: 설치 직후 bootstrap.sh 가 실행해 환경을 점검한다."""
import numpy as np
import pandas as pd
import pytest

from harness.scaffold import analysis_utils as au


def test_parse_dates_strict_mixed_formats():
    s = pd.Series(["2026-10-03", "10/04/2026", "20261005"])
    out = au.parse_dates_strict(s, ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"])
    assert list(out.dt.day) == [3, 4, 5]


def test_parse_dates_strict_raises_on_unknown():
    with pytest.raises(ValueError):
        au.parse_dates_strict(pd.Series(["2026.10.03"]), ["%Y-%m-%d"])


def test_infer_slash_order():
    assert au.infer_slash_order(pd.Series(["10/03/2026", "10/23/2026"])) == "MDY"
    assert au.infer_slash_order(pd.Series(["23/10/2026", "03/10/2026"])) == "DMY"
    assert au.infer_slash_order(pd.Series(["10/03/2026"])) == "ambiguous"


def test_normalize_categories():
    m = {"CH-B": "B", "ChB": "B", "B": "B", "CH-A": "A"}
    out = au.normalize_categories(pd.Series([" ch-b", "CHB", "b", "CH-A"]), m)
    assert list(out) == ["B", "B", "B", "A"]
    with pytest.raises(ValueError):
        au.normalize_categories(pd.Series(["CH-X"]), m)


def test_dedupe_keep_first_and_last():
    df = pd.DataFrame({"lot": ["L1", "L1", "L2"], "w": [1, 1, 1], "seq": [2, 1, 1], "y": [0.9, 0.8, 0.7]})
    kept, removed = au.dedupe_keep(df, ["lot", "w"], "seq", "first")
    assert sorted(kept["y"]) == [0.7, 0.8] and len(removed) == 1
    kept, _ = au.dedupe_keep(df, ["lot", "w"], "seq", "last")
    assert sorted(kept["y"]) == [0.7, 0.9]


def test_isolate_out_of_range():
    df = pd.DataFrame({"y": [0.5, 1.2, np.nan]})
    ok, bad = au.isolate_out_of_range(df, "y", 0, 1)
    assert len(ok) == 1 and len(bad) == 2


def test_join_report():
    left = pd.DataFrame({"lot": ["L1", "L2", "L3"], "v": [1, 2, 3]})
    right = pd.DataFrame({"lot": ["L1", "L2"], "ch": ["A", "B"]})
    merged, lost, ratio = au.join_report(left, right, "lot")
    assert len(merged) == 2 and list(lost["lot"]) == ["L3"] and abs(ratio - 1 / 3) < 1e-9


def test_unit_level_rejects_varying_factor():
    df = pd.DataFrame({"lot": ["L1", "L1"], "y": [0.8, 0.9], "ch": ["A", "B"]})
    with pytest.raises(ValueError):
        au.unit_level(df, "lot", "y", ["ch"])


def _synthetic():
    rng = np.random.default_rng(1)
    rows = []
    for i in range(60):
        ch = "B" if i % 2 else "A"
        mat = "new" if (i % 5 == 0) else "old"
        base = 0.78 if ch == "B" else 0.90
        for w in range(5):
            rows.append({"lot": f"L{i}", "ch": ch, "mat": mat, "y": base + rng.normal(0, 0.01),
                         "date": pd.Timestamp("2026-10-01") + pd.Timedelta(days=i // 6)})
    return pd.DataFrame(rows)


def test_stratify_and_crosstab_and_naive():
    df = _synthetic()
    st = au.stratify(df, ["ch", "mat"], "y", unit_col="lot", baseline=0.90)
    b = st[st["ch"] == "B"]["diff_vs_baseline"]
    assert (b < -0.1).all()
    assert st["n"].sum() == 60
    ct = au.crosstab_counts(df, "ch", "mat", unit_col="lot")
    assert ct.loc["All", "All"] == 60
    res = au.naive_vs_stratified(df, "mat", "ch", "y", unit_col="lot")
    assert set(res["stratified"].index) == {"A", "B"}


def test_trend_period_bootstrap():
    df = _synthetic()
    tr = au.daily_trend(df, "date", "y", unit_col="lot")
    assert {"day", "mean", "n_units"} <= set(tr.columns)
    pc = au.period_compare(df, "date", "y", "2026-10-05", unit_col="lot")
    assert "diff(after-before)" in set(pc["period"])
    lots = au.unit_level(df, "lot", "y", ["ch"])
    r = au.bootstrap_diff(lots[lots.ch == "B"]["y"], lots[lots.ch == "A"]["y"], n=300)
    assert r["ci_high"] < 0


def test_radial_profile_edge_loss():
    xs, ys = np.meshgrid(np.arange(-10, 11), np.arange(-10, 11))
    d = pd.DataFrame({"x": xs.ravel(), "y": ys.ravel()})
    d = d[np.hypot(d.x, d.y) <= 10]
    d["pass"] = (np.hypot(d.x, d.y) < 8).astype(int)
    rp = au.radial_profile(d, "x", "y", "pass", n_bins=5)
    assert rp.iloc[0]["pass_rate"] == 1.0 and rp.iloc[-1]["pass_rate"] < 0.5


def test_profile_and_plots(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    df = _synthetic()
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    md = au.profile(df, "synthetic", key_cols=["lot"])
    assert "## synthetic" in md and "date_str" in md
    tr = au.daily_trend(df, "date", "y", group_col="ch", unit_col="lot")
    p1 = au.save_fig(au.plot_trend(tr, [("2026-10-04", "event")], group_col="ch"), "t")
    table, fig = au.waterfall([("measure", -0.015), ("chamber", -0.06), ("residual", 0.001)],
                              start_value=0.91)
    p2 = au.save_fig(fig, "w")
    p3 = au.save_table(table, "w")
    for p in (p1, p2, p3):
        assert (tmp_path / p).exists()
