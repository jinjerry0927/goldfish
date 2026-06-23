"""CSV 로더 테스트 — 인코딩 처리 및 천단위 쉼표 자동 변환."""
from __future__ import annotations

import pandas as pd
import pytest
from pandas.api import types as ptypes

from goldfish.loaders.csv import load_csv


def _write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return path


def test_load_csv_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_csv(tmp_path / "없는파일.csv")


def test_thousands_comma_columns_become_numeric(tmp_path):
    csv = _write(
        tmp_path / "t.csv",
        "체결일,종목명,매매구분,수량,단가,거래금액,종목코드,실현손익\n"
        "2026-05-04,TIGER,매수,39,\"26,150\",\"1,019,850\",360750,0\n"
        "2026-05-21,TIGER,매도,30,43425,\"1,299,750\",396500,\"73,410\"\n",
    )
    df = load_csv(csv)
    # 쉼표가 있던 숫자 컬럼이 숫자형으로 변환되어야 한다
    assert ptypes.is_numeric_dtype(df["단가"])
    assert ptypes.is_numeric_dtype(df["거래금액"])
    assert ptypes.is_numeric_dtype(df["실현손익"])
    assert df["단가"].iloc[0] == 26150
    assert df["거래금액"].iloc[1] == 1299750
    assert df["실현손익"].iloc[1] == 73410


def test_identifier_column_preserved_as_string(tmp_path):
    # 종목코드는 쉼표 변환 대상에서 제외(앞자리 0/문자 보존)
    csv = _write(
        tmp_path / "t.csv",
        "종목코드,종목명,단가\n005930,삼성전자,\"72,000\"\n0183J0,TIGER미국,\"9,990\"\n",
    )
    df = load_csv(csv)
    assert not ptypes.is_numeric_dtype(df["종목코드"])
    assert df["종목코드"].iloc[0] == "005930"
    assert df["종목코드"].iloc[1] == "0183J0"
    assert ptypes.is_numeric_dtype(df["단가"])


def test_text_columns_with_commas_not_corrupted(tmp_path):
    # 쉼표가 든 '텍스트' 컬럼은 숫자로 바뀌면 안 된다
    csv = _write(
        tmp_path / "t.csv",
        "메모,수량\n\"매수, 분할\",10\n\"장기, 보유\",20\n",
    )
    df = load_csv(csv)
    assert not ptypes.is_numeric_dtype(df["메모"])
    assert df["메모"].iloc[0] == "매수, 분할"


def test_plain_numeric_unaffected(tmp_path):
    # 쉼표 없는 일반 숫자는 기존대로 숫자형
    csv = _write(tmp_path / "t.csv", "수량,단가\n10,72000\n5,48000\n")
    df = load_csv(csv)
    assert ptypes.is_numeric_dtype(df["수량"])
    assert ptypes.is_numeric_dtype(df["단가"])
    assert df["단가"].iloc[0] == 72000


def test_cp949_encoding_fallback(tmp_path):
    # 엑셀 한글 CSV(cp949)도 읽혀야 한다
    csv = _write(
        tmp_path / "t.csv",
        "종목명,수량\n삼성전자,10\n카카오,5\n",
        encoding="cp949",
    )
    df = load_csv(csv)
    assert list(df["종목명"]) == ["삼성전자", "카카오"]
