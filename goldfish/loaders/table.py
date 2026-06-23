"""표 로더 — CSV/엑셀(xlsx) 파일을 동일한 DataFrame 으로 읽는다.

워크스페이스 폴더 일괄 분석에서 사용한다. 천단위 쉼표·빈 행을 정리하고,
엑셀은 ``openpyxl`` 이 있을 때만 지원한다.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from goldfish.loaders.csv import _coerce_numeric_with_commas, load_csv

EXCEL_SUFFIXES = frozenset({".xlsx", ".xls", ".xlsm"})


def load_table(path: str | Path) -> pd.DataFrame:
    """확장자에 맞춰 CSV/엑셀을 읽어 정리된 DataFrame 을 반환한다.

    Raises:
        FileNotFoundError: 파일이 없을 때.
        RuntimeError: 엑셀인데 ``openpyxl`` 이 설치돼 있지 않을 때.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    if path.suffix.lower() in EXCEL_SUFFIXES:
        try:
            # 전부 문자열로 읽어 종목코드 앞자리 0 보존 → 숫자 컬럼만 변환
            df = pd.read_excel(path, dtype=str)
        except ImportError as e:  # openpyxl 미설치
            raise RuntimeError(
                "엑셀(xlsx) 을 읽으려면 openpyxl 이 필요합니다: pip install openpyxl"
            ) from e
        df.columns = [str(c).strip() for c in df.columns]
        df = _coerce_numeric_with_commas(df, require_comma=False)
    else:
        df = load_csv(path)

    # 완전히 빈 행 제거(엑셀 양식의 미입력 행 등)
    df = df.dropna(how="all").reset_index(drop=True)
    return df
