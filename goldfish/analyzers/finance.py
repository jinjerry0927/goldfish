"""금융 특화 진단 — AI/토스 없이 순수 pandas 로 동작.

거래내역(체결) 데이터를 받아 범용 통계를 넘어선 "투자자 습관" 진단을 dict 로
반환한다. basic analyzer 와 마찬가지로 결과는 평범한 dict 라서 텍스트/HTML/AI
계층이 자유롭게 얹힐 수 있다.

표준 스키마(한글 컬럼 가정):
    필수: 체결일, 종목명, 매매구분, 수량, 단가, 거래금액
    선택: 종목코드(식별자), 실현손익

⚠️ 진단·설명용이며 투자 추천이 아니다.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# 표준 스키마 ----------------------------------------------------------------
REQUIRED_COLUMNS = ["체결일", "종목명", "매매구분", "수량", "단가", "거래금액"]
OPTIONAL_COLUMNS = ["종목코드", "실현손익"]
# 식별자 컬럼: 수치로 읽혀도 통계 대상이 아님(앞자리 0 손실 주의 → 문자열 취급)
IDENTIFIER_COLUMNS = ["종목코드"]

BUY = "매수"
SELL = "매도"

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def validate_schema(df: pd.DataFrame) -> dict[str, Any]:
    """거래내역 스키마를 검증한다.

    Returns:
        dict: ``valid``(필수 컬럼 모두 존재), ``missing``(없는 필수 컬럼),
        ``optional_present``(존재하는 선택 컬럼).
    """
    cols = set(df.columns)
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
    return {
        "valid": not missing,
        "missing": missing,
        "optional_present": [c for c in OPTIONAL_COLUMNS if c in cols],
    }


def is_finance_df(df: pd.DataFrame) -> bool:
    """필수 컬럼이 모두 있으면 금융 거래내역으로 간주한다."""
    return validate_schema(df)["valid"]


def _concentration(df: pd.DataFrame, top_n: int = 3) -> dict[str, Any]:
    """포트폴리오 집중도/분산 — 거래금액 기준 종목별 비중.

    실제 보유 비중 데이터가 없으므로 '거래 활동' 기준(거래금액 합) 집중도를 본다.
    HHI(허핀달지수)와 상위 N 종목 편중도를 함께 제공한다.
    """
    amt = df.groupby("종목명")["거래금액"].sum().sort_values(ascending=False)
    total = float(amt.sum())
    if total <= 0:
        return {"stocks": 0, "by_stock": [], "top_n": top_n, "top_n_share": 0.0, "hhi": 0.0}

    shares = (amt / total * 100).round(2)
    hhi = float(((amt / total) ** 2).sum())  # 0~1 (1=완전집중)

    by_stock = [
        {"name": name, "amount": float(a), "share": float(shares[name])}
        for name, a in amt.items()
    ]
    return {
        "stocks": int(amt.size),
        "by_stock": by_stock,
        "top1_share": float(shares.iloc[0]),
        "top_n": top_n,
        "top_n_share": float(shares.iloc[:top_n].sum()),
        "hhi": round(hhi, 4),
    }


def _trading_pattern(df: pd.DataFrame) -> dict[str, Any]:
    """매매 패턴 — 매수/매도 빈도, 거래 시간대(요일/시각) 분포, 과매매 지표."""
    side = df["매매구분"]
    buy_n = int((side == BUY).sum())
    sell_n = int((side == SELL).sum())

    dt = pd.to_datetime(df["체결일"], errors="coerce")
    valid_dt = dt.dropna()
    active_days = int(valid_dt.dt.normalize().nunique()) if not valid_dt.empty else 0
    total_trades = int(len(df))

    # 시간 정보가 있으면 시각대, 없으면 요일 분포로 대체
    has_time = bool((valid_dt.dt.hour != 0).any() or (valid_dt.dt.minute != 0).any())
    if has_time:
        dist_kind = "hour"
        counts = valid_dt.dt.hour.value_counts().sort_index()
        distribution = {int(h): int(c) for h, c in counts.items()}
    else:
        dist_kind = "weekday"
        counts = valid_dt.dt.weekday.value_counts()
        distribution = {_WEEKDAYS[int(w)]: int(c) for w, c in counts.sort_index().items()}

    # 과매매 지표: 거래일당 평균 체결 수, 하루 최대 체결 수
    per_day = valid_dt.dt.normalize().value_counts() if not valid_dt.empty else pd.Series(dtype=int)
    return {
        "buy_count": buy_n,
        "sell_count": sell_n,
        "buy_sell_ratio": round(buy_n / sell_n, 2) if sell_n else None,
        "active_days": active_days,
        "total_trades": total_trades,
        "trades_per_active_day": round(total_trades / active_days, 2) if active_days else 0.0,
        "max_trades_in_a_day": int(per_day.max()) if not per_day.empty else 0,
        "distribution_kind": dist_kind,
        "distribution": distribution,
    }


def _realized_pnl(df: pd.DataFrame) -> dict[str, Any] | None:
    """손절·익절 습관 — 실현손익 분포(승률, 손익비 등). 컬럼 없으면 None."""
    if "실현손익" not in df.columns:
        return None

    pnl = pd.to_numeric(df["실현손익"], errors="coerce").fillna(0)
    realized = pnl[pnl != 0]  # 실현(주로 매도)에서만 손익 발생
    if realized.empty:
        return {"realized_trades": 0}

    wins = realized[realized > 0]
    losses = realized[realized < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())  # 음수
    return {
        "realized_trades": int(realized.size),
        "wins": int(wins.size),
        "losses": int(losses.size),
        "win_rate": round(wins.size / realized.size * 100, 2),
        "total_pnl": float(realized.sum()),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "avg_win": float(wins.mean()) if not wins.empty else 0.0,
        "avg_loss": float(losses.mean()) if not losses.empty else 0.0,
        "profit_factor": round(gross_profit / abs(gross_loss), 2) if gross_loss != 0 else None,
        "biggest_win": float(realized.max()),
        "biggest_loss": float(realized.min()),
    }


def _returns(df: pd.DataFrame) -> dict[str, Any] | None:
    """수익률·변동성 — 실현손익 기반 근사. 보유평가액 시계열이 없어 추정치다.

    매도 체결의 매도금액 = 거래금액, 원가 = 거래금액 - 실현손익 으로 보고
    체결별 실현 수익률(%)을 구한 뒤 평균/표준편차(변동성)를 낸다.
    """
    if "실현손익" not in df.columns:
        return None

    pnl = pd.to_numeric(df["실현손익"], errors="coerce").fillna(0)
    amount = pd.to_numeric(df["거래금액"], errors="coerce")
    sells = (df["매매구분"] == SELL) & (pnl != 0)
    if not sells.any():
        return {"sell_trades": 0}

    proceeds = amount[sells]
    realized = pnl[sells]
    cost = proceeds - realized
    valid = cost > 0
    ret_pct = (realized[valid] / cost[valid] * 100) if valid.any() else pd.Series(dtype=float)

    total_cost = float(cost[valid].sum()) if valid.any() else 0.0
    total_pnl = float(realized[valid].sum()) if valid.any() else 0.0
    return {
        "sell_trades": int(sells.sum()),
        "total_realized_pnl": total_pnl,
        "total_cost_basis": total_cost,
        "realized_return_pct": round(total_pnl / total_cost * 100, 2) if total_cost else 0.0,
        "avg_trade_return_pct": round(float(ret_pct.mean()), 2) if not ret_pct.empty else 0.0,
        "return_volatility_pct": round(float(ret_pct.std()), 2)
        if ret_pct.size > 1
        else 0.0,
    }


def analyze_finance(df: pd.DataFrame, top_n: int = 3) -> dict[str, Any]:
    """거래내역 DataFrame 에 대한 금융 특화 진단을 dict 로 반환한다.

    Raises:
        ValueError: 필수 컬럼이 빠져 스키마 검증에 실패한 경우.
    """
    schema = validate_schema(df)
    if not schema["valid"]:
        raise ValueError(
            "금융 거래내역 스키마가 아닙니다. 누락된 필수 컬럼: "
            + ", ".join(schema["missing"])
        )

    return {
        "schema": schema,
        "concentration": _concentration(df, top_n=top_n),
        "trading": _trading_pattern(df),
        "pnl": _realized_pnl(df),
        "returns": _returns(df),
    }
