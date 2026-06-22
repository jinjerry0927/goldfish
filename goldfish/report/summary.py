"""자연어 요약 추출 API — DataFrame 한 개로 분석→AI 요약까지 묶는 편의 계층.

CLI 와 (향후) HTML 리포트가 공통으로 쓰는 진입점이다. AI 가 준비돼 있지
않으면(키 없음·미설치) 예외 대신 ``None`` 을 돌려주어 "통계만" fallback 이
자연스럽게 되도록 한다.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from goldfish import ai
from goldfish.analyzers.basic import analyze_basic
from goldfish.analyzers.finance import analyze_finance, is_finance_df


def summary(
    df: pd.DataFrame,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[str]:
    """DataFrame 을 분석하고 AI 자연어 요약을 반환한다.

    AI 를 쓸 수 없으면(키 없음·라이브러리 미설치) ``None`` 을 반환한다
    (호출 측은 통계만 출력하면 된다).

    Raises:
        ai.AIUnavailable: 키·라이브러리는 준비됐으나 호출 자체가 실패한 경우
            (네트워크 오류, 빈 응답 등). 준비 안 됨과 실패를 구분하기 위함.
    """
    if not ai.available(api_key):
        return None

    basic = analyze_basic(df)
    finance: dict[str, Any] | None = analyze_finance(df) if is_finance_df(df) else None

    kwargs: dict[str, Any] = {"api_key": api_key}
    if model is not None:
        kwargs["model"] = model
    return ai.summarize(basic, finance, **kwargs)
