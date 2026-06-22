"""CSV 로더 — 파일 경로를 받아 pandas DataFrame 으로 변환."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_csv(path: str | Path, **read_csv_kwargs) -> pd.DataFrame:
    """CSV 파일을 읽어 DataFrame 으로 반환한다.

    한글 컬럼/BOM 을 위해 기본 인코딩은 ``utf-8-sig`` 이며, 실패 시
    ``cp949`` (엑셀 한글 CSV) 로 한 번 더 시도한다.

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
        return pd.read_csv(path, encoding=encoding, **read_csv_kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", **read_csv_kwargs)
