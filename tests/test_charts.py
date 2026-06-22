"""charts 모듈 동작 테스트 — 파일 생성/스킵 여부 위주(시각 정확성은 검증 안 함)."""
from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("matplotlib")

from goldfish.report import charts  # noqa: E402


def _trades_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "체결일": ["2025-06-02", "2025-06-02", "2025-06-03", "2025-06-04"],
            "종목명": ["가나전자", "가나전자", "다라반도체", "다라반도체"],
            "매매구분": ["매수", "매도", "매수", "매도"],
            "수량": [10, 5, 8, 8],
            "단가": [100.0, 120.0, 200.0, 250.0],
            "거래금액": [1000, 600, 1600, 2000],
            "실현손익": [0, 100, 0, -50],
        }
    )


def test_save_all_creates_three_pngs(tmp_path):
    saved = charts.save_all(_trades_df(), tmp_path)
    assert len(saved) == 3
    for p in saved:
        assert p.exists()
        assert p.stat().st_size > 0


def test_concentration_chart_returns_none_when_no_amount(tmp_path):
    df = _trades_df().assign(거래금액=0)
    assert charts.concentration_chart(df, tmp_path / "c.png") is None
    assert not (tmp_path / "c.png").exists()


def test_pnl_histogram_skipped_without_column(tmp_path):
    df = _trades_df().drop(columns=["실현손익"])
    assert charts.pnl_histogram(df, tmp_path / "h.png") is None
    # 실현손익 없으면 save_all 은 차트 2개만 생성
    saved = charts.save_all(df, tmp_path)
    assert len(saved) == 2


def test_trading_distribution_chart_created(tmp_path):
    p = charts.trading_distribution_chart(_trades_df(), tmp_path / "t.png")
    assert p is not None and p.exists()
