"""기본 프로파일링 — AI/토스 없이 순수 pandas 로 동작.

``analyze_basic(df)`` 가 분석 결과를 평범한 dict 로 반환하므로,
텍스트/HTML 리포트나 AI 요약 계층이 그 위에 자유롭게 얹힐 수 있다.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _overview(df: pd.DataFrame) -> dict[str, Any]:
    """행/열 수, 컬럼별 데이터 타입."""
    return {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


def _missing(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """컬럼별 결측치 개수와 비율(%). 결측이 있는 컬럼만 반환."""
    total = len(df)
    out: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n:
            out[col] = {"count": n, "pct": round(n / total * 100, 2) if total else 0.0}
    return out


def _distribution(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """수치형 컬럼의 분포 통계(평균/중앙/표준편차/분위/최소·최대)."""
    num = df.select_dtypes(include=[np.number])
    out: dict[str, dict[str, float]] = {}
    for col in num.columns:
        s = num[col].dropna()
        if s.empty:
            continue
        out[col] = {
            "mean": float(s.mean()),
            "median": float(s.median()),
            "std": float(s.std()),
            "min": float(s.min()),
            "q25": float(s.quantile(0.25)),
            "q75": float(s.quantile(0.75)),
            "max": float(s.max()),
        }
    return out


def _outliers_iqr(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """IQR(1.5배) 기준 이상치 개수. 이상치가 있는 수치형 컬럼만 반환."""
    num = df.select_dtypes(include=[np.number])
    out: dict[str, dict[str, Any]] = {}
    for col in num.columns:
        s = num[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (s < low) | (s > high)
        n = int(mask.sum())
        if n:
            out[col] = {
                "count": n,
                "pct": round(n / len(s) * 100, 2),
                "lower": float(low),
                "upper": float(high),
            }
    return out


def _correlation(df: pd.DataFrame) -> dict[str, Any]:
    """수치형 컬럼 간 상관계수와, |상관| 상위 페어."""
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        return {"matrix": {}, "top_pairs": []}

    corr = num.corr(numeric_only=True)
    pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr.iloc[i, j]
            if pd.notna(val):
                pairs.append((cols[i], cols[j], float(val)))
    pairs.sort(key=lambda p: abs(p[2]), reverse=True)

    return {
        "matrix": {c: {k: float(v) for k, v in corr[c].items()} for c in corr.columns},
        "top_pairs": [
            {"a": a, "b": b, "corr": round(v, 3)} for a, b, v in pairs[:5]
        ],
    }


def analyze_basic(df: pd.DataFrame) -> dict[str, Any]:
    """DataFrame 에 대한 기본 프로파일링 결과를 dict 로 반환한다."""
    return {
        "overview": _overview(df),
        "missing": _missing(df),
        "distribution": _distribution(df),
        "outliers": _outliers_iqr(df),
        "correlation": _correlation(df),
    }
