"""표 로더(load_table) — CSV/엑셀 공통 읽기 및 정리 테스트."""
from __future__ import annotations

import pandas as pd
import pytest
from pandas.api import types as ptypes

from goldfish.loaders.table import load_table


def test_load_table_csv_with_commas(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text(
        "종목명,수량,단가\n삼성전자,10,\"72,000\"\n카카오,5,48000\n",
        encoding="utf-8",
    )
    df = load_table(p)
    assert ptypes.is_numeric_dtype(df["단가"])
    assert df["단가"].iloc[0] == 72000


def test_load_table_xlsx_numeric_and_identifier(tmp_path):
    pytest.importorskip("openpyxl")
    p = tmp_path / "t.xlsx"
    pd.DataFrame(
        {
            "종목명": ["삼성전자", "TIGER미국"],
            "수량": [10, 5],
            "단가": [72000, 9990],
            "종목코드": ["005930", "0183J0"],
        }
    ).to_excel(p, index=False)
    df = load_table(p)
    # 엑셀 숫자 컬럼은 숫자로, 종목코드는 문자열(앞자리 0 보존)
    assert ptypes.is_numeric_dtype(df["단가"])
    assert df["단가"].iloc[0] == 72000
    assert not ptypes.is_numeric_dtype(df["종목코드"])
    assert df["종목코드"].iloc[0] == "005930"


def test_load_table_drops_empty_rows(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("종목명,수량\n삼성전자,10\n,\n,\n", encoding="utf-8")
    df = load_table(p)
    assert len(df) == 1


def test_load_table_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_table(tmp_path / "none.csv")
