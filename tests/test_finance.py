"""finance analyzer 핵심 동작 테스트."""
from __future__ import annotations

import pandas as pd
import pytest

from goldfish.analyzers.finance import (
    analyze_finance,
    is_finance_df,
    validate_schema,
)
from goldfish.report.text import render_finance


def _trades_df() -> pd.DataFrame:
    """매수/매도가 섞인 작은 거래내역. 가나전자에 거래가 편중되어 있다."""
    return pd.DataFrame(
        {
            "체결일": [
                "2025-06-02",  # 월
                "2025-06-02",
                "2025-06-03",  # 화
                "2025-06-04",  # 수
                "2025-06-04",
            ],
            "종목코드": ["005930", "005930", "005930", "000660", "000660"],
            "종목명": ["가나전자", "가나전자", "가나전자", "다라반도체", "다라반도체"],
            "매매구분": ["매수", "매도", "매도", "매수", "매도"],
            "수량": [10, 5, 5, 8, 8],
            "단가": [100.0, 120.0, 90.0, 200.0, 250.0],
            "거래금액": [1000, 600, 450, 1600, 2000],
            "실현손익": [0, 100, -50, 0, 400],
        }
    )


def test_validate_schema_ok():
    res = validate_schema(_trades_df())
    assert res["valid"] is True
    assert res["missing"] == []
    assert set(res["optional_present"]) == {"종목코드", "실현손익"}


def test_validate_schema_missing_required():
    df = _trades_df().drop(columns=["거래금액", "매매구분"])
    res = validate_schema(df)
    assert res["valid"] is False
    assert set(res["missing"]) == {"거래금액", "매매구분"}
    assert is_finance_df(df) is False


def test_analyze_finance_raises_on_bad_schema():
    with pytest.raises(ValueError):
        analyze_finance(pd.DataFrame({"a": [1], "b": [2]}))


def test_concentration_shares_and_top():
    conc = analyze_finance(_trades_df())["concentration"]
    # 가나전자 거래금액 합 2050, 다라반도체 3600, 총 5650
    assert conc["stocks"] == 2
    # 가장 비중 큰 종목이 top1
    assert conc["by_stock"][0]["name"] == "다라반도체"
    assert round(conc["top1_share"], 1) == round(3600 / 5650 * 100, 1)
    assert 0 < conc["hhi"] <= 1
    # 전 종목 비중 합은 100%
    assert round(sum(s["share"] for s in conc["by_stock"]), 0) == 100


def test_trading_pattern_counts():
    tr = analyze_finance(_trades_df())["trading"]
    assert tr["buy_count"] == 2
    assert tr["sell_count"] == 3
    assert tr["active_days"] == 3
    assert tr["total_trades"] == 5
    assert tr["max_trades_in_a_day"] == 2
    # 시각 정보 없는 날짜 → 요일 분포
    assert tr["distribution_kind"] == "weekday"


def test_realized_pnl_win_rate_and_profit_factor():
    pnl = analyze_finance(_trades_df())["pnl"]
    # 실현손익 0 이 아닌 건: +100, -50, +400 → 3건, 익절 2 / 손절 1
    assert pnl["realized_trades"] == 3
    assert pnl["wins"] == 2
    assert pnl["losses"] == 1
    assert pnl["total_pnl"] == 450
    assert pnl["profit_factor"] == round(500 / 50, 2)
    assert pnl["biggest_loss"] == -50


def test_pnl_none_when_column_absent():
    df = _trades_df().drop(columns=["실현손익"])
    res = analyze_finance(df)
    assert res["pnl"] is None
    assert res["returns"] is None


def test_returns_realized_estimate():
    ret = analyze_finance(_trades_df())["returns"]
    assert ret["sell_trades"] == 3
    # 원가 = 거래금액 - 실현손익; 매도 3건만 집계
    assert ret["total_realized_pnl"] == 450
    assert ret["realized_return_pct"] != 0.0


def test_render_finance_runs_and_has_disclaimer():
    text = render_finance(analyze_finance(_trades_df()))
    assert "금융 특화 진단" in text
    assert "투자 추천이 아닙니다" in text
    assert "승률" in text
