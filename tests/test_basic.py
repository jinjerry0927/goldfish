"""basic analyzer 핵심 동작 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd

from goldfish.analyzers.basic import analyze_basic
from goldfish.report.text import render_text


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["a", "b", "c", "d", "e"],
            "x": [1, 2, 3, 4, 100],          # 100 = 이상치
            "y": [2, 4, 6, 8, 200],          # x 와 강한 양의 상관
            "missing_col": [1.0, np.nan, 3.0, np.nan, 5.0],
        }
    )


def test_overview_shape_and_dtypes():
    res = analyze_basic(_sample_df())
    ov = res["overview"]
    assert ov["rows"] == 5
    assert ov["cols"] == 4
    assert set(ov["dtypes"]) == {"name", "x", "y", "missing_col"}


def test_missing_counts_only_columns_with_na():
    res = analyze_basic(_sample_df())
    missing = res["missing"]
    assert missing["missing_col"]["count"] == 2
    assert missing["missing_col"]["pct"] == 40.0
    assert "x" not in missing  # 결측 없는 컬럼은 제외


def test_distribution_numeric_only():
    res = analyze_basic(_sample_df())
    dist = res["distribution"]
    assert "name" not in dist  # 문자열 컬럼 제외
    assert dist["x"]["min"] == 1.0
    assert dist["x"]["max"] == 100.0
    assert dist["x"]["median"] == 3.0


def test_outliers_iqr_detects_extreme_value():
    res = analyze_basic(_sample_df())
    outliers = res["outliers"]
    assert "x" in outliers
    assert outliers["x"]["count"] >= 1


def test_correlation_top_pairs_sorted_by_abs():
    res = analyze_basic(_sample_df())
    top = res["correlation"]["top_pairs"]
    assert top, "상관 페어가 비어 있으면 안 됨"
    # x↔y 는 강한 양의 상관 → 최상위
    first = top[0]
    assert {first["a"], first["b"]} == {"x", "y"}
    assert first["corr"] > 0.9


def test_empty_numeric_is_safe():
    df = pd.DataFrame({"name": ["a", "b"], "label": ["x", "y"]})
    res = analyze_basic(df)
    assert res["distribution"] == {}
    assert res["outliers"] == {}
    assert res["correlation"]["top_pairs"] == []


def test_render_text_runs_and_includes_disclaimer():
    text = render_text(analyze_basic(_sample_df()))
    assert "GoldFish" in text
    assert "투자 추천이 아닙니다" in text
