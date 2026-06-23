"""CSV 로더 — 파일 경로를 받아 pandas DataFrame 으로 변환."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.api import types as ptypes

# 천단위 쉼표가 들어 있어도 숫자로 바꾸면 안 되는 식별자 컬럼.
# (예: 종목코드 "005930" 은 앞자리 0/문자가 섞여 식별자이므로 문자열 유지)
IDENTIFIER_COLS = frozenset({"종목코드", "계좌번호", "주문번호"})


def _coerce_numeric_with_commas(
    df: pd.DataFrame, *, require_comma: bool = True
) -> pd.DataFrame:
    """천단위 쉼표가 든 숫자 컬럼(예: ``"1,234"``)을 숫자로 변환한다.

    한국 증권사 CSV/엑셀은 단가·거래금액·실현손익 등을 ``"26,150"`` 처럼
    쉼표가 포함된 채로 내보내는 경우가 많아, 그대로 두면 컬럼 전체가 문자열로
    읽혀 수치 분석이 동작하지 않는다.

    식별자 컬럼(:data:`IDENTIFIER_COLS`)과, 변환 시 숫자가 아닌 값이 섞인
    컬럼은 건드리지 않는다(텍스트 컬럼 보호).

    Args:
        require_comma: ``True`` 면 **쉼표가 실제로 든 컬럼만** 변환한다(CSV용,
            기존 동작 보존). ``False`` 면 전부 문자열로 읽은 경우(xlsx 등)에
            맞춰 숫자로 보이는 컬럼을 모두 변환한다.
    """
    for col in df.columns:
        if col in IDENTIFIER_COLS:
            continue
        s = df[col]
        if ptypes.is_numeric_dtype(s):
            continue  # 이미 숫자면 손대지 않음
        as_str = s.astype(str)
        if require_comma and not as_str.str.contains(",", na=False).any():
            continue  # 쉼표 없으면 손대지 않음
        cleaned = as_str.str.replace(",", "", regex=False).str.strip()
        converted = pd.to_numeric(cleaned, errors="coerce")
        # 원래 값이 있던 칸이 모두 숫자로 변환됐을 때만 적용(텍스트 컬럼 보호)
        present = s.notna() & (as_str.str.strip() != "")
        if present.any() and converted[present].notna().all():
            df[col] = converted
    return df


def load_csv(path: str | Path, **read_csv_kwargs) -> pd.DataFrame:
    """CSV 파일을 읽어 DataFrame 으로 반환한다.

    한글 컬럼/BOM 을 위해 기본 인코딩은 ``utf-8-sig`` 이며, 실패 시
    ``cp949`` (엑셀 한글 CSV) 로 한 번 더 시도한다. 읽은 뒤에는 천단위
    쉼표가 든 숫자 컬럼을 자동으로 숫자형으로 변환한다.

    Args:
        path: CSV 파일 경로.
        **read_csv_kwargs: ``pandas.read_csv`` 로 그대로 전달되는 추가 옵션.

    Raises:
        FileNotFoundError: 경로에 파일이 없을 때.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}")

    encoding = read_csv_kwargs.pop("encoding", "utf-8-sig")
    try:
        df = pd.read_csv(path, encoding=encoding, **read_csv_kwargs)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949", **read_csv_kwargs)
    return _coerce_numeric_with_commas(df)
