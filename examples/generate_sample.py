"""합성 거래 데이터 생성 스크립트 — 개인정보 無, 재현 가능(seed 고정).

실행:
    python examples/generate_sample.py [--rows 500] [--seed 42] [--out examples/sample.csv]

생성 컬럼:
    체결일(date), 종목코드(ticker), 종목명(name), 매매구분(side: 매수/매도),
    수량(qty), 단가(price), 거래금액(amount), 실현손익(realized_pnl)

⚠️ 실제 거래·고객 데이터가 아닌 100% 합성 데이터입니다. (기획서 안전 원칙 4)
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd

# (종목코드, 종목명, 기준가) — 가상의 종목 풀
UNIVERSE: list[tuple[str, str, float]] = [
    ("005930", "가나전자", 70000),
    ("000660", "다라반도체", 130000),
    ("035420", "마바인터넷", 200000),
    ("051910", "사아화학", 450000),
    ("207940", "자차바이오", 800000),
    ("373220", "카타배터리", 400000),
    ("035720", "파하소프트", 55000),
    ("068270", "아자제약", 180000),
]


def generate(rows: int = 500, seed: int = 42) -> pd.DataFrame:
    """합성 거래 내역 DataFrame 을 반환한다."""
    rng = np.random.default_rng(seed)

    # 최근 1년 영업일 범위에서 체결일 샘플링
    end = date(2026, 6, 1)
    start = end - timedelta(days=365)
    all_days = pd.bdate_range(start, end)
    trade_dates = rng.choice(all_days, size=rows)

    picks = rng.integers(0, len(UNIVERSE), size=rows)
    sides = rng.choice(["매수", "매도"], size=rows, p=[0.55, 0.45])

    records = []
    for i in range(rows):
        ticker, name, base = UNIVERSE[picks[i]]
        # 기준가 대비 ±15% 변동
        price = round(base * rng.uniform(0.85, 1.15), -1)
        qty = int(rng.integers(1, 50))
        amount = round(price * qty)
        # 매도일 때만 실현손익 발생(매수는 0)
        if sides[i] == "매도":
            pnl = round(amount * rng.normal(0.01, 0.08))
        else:
            pnl = 0
        records.append(
            {
                "체결일": pd.Timestamp(trade_dates[i]).date().isoformat(),
                "종목코드": ticker,
                "종목명": name,
                "매매구분": sides[i],
                "수량": qty,
                "단가": price,
                "거래금액": amount,
                "실현손익": pnl,
            }
        )

    df = pd.DataFrame.from_records(records)
    return df.sort_values("체결일").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="goldfish 합성 거래 데이터 생성")
    parser.add_argument("--rows", type=int, default=500, help="생성할 거래 행 수")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드(재현용)")
    parser.add_argument(
        "--out", default="examples/sample.csv", help="출력 CSV 경로"
    )
    args = parser.parse_args()

    df = generate(rows=args.rows, seed=args.seed)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"[OK] {len(df)} rows -> {args.out}")


if __name__ == "__main__":
    main()
