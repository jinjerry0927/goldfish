"""차트 생성 — 거래내역 DataFrame → PNG 이미지 파일.

matplotlib(선택 의존성, ``pip install goldfish[charts]``)을 사용한다. 화면이
없는 환경에서도 동작하도록 비대화형 ``Agg`` 백엔드를 강제하며, 한글 컬럼명이
깨지지 않도록 사용 가능한 한글 폰트를 자동 선택한다.

각 함수는 "df → png 경로" 인터페이스를 따르며, 그릴 데이터가 없으면 ``None``
을 반환한다(파일을 만들지 않음).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 디스플레이 없는 환경 대비
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from goldfish.analyzers.finance import SELL, _trading_pattern  # noqa: E402

# 한글 폰트 자동 선택 (없으면 기본값 유지 — 글자가 깨질 수 있으나 크래시는 없음)
_KOREAN_FONTS = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"]


def _apply_korean_font() -> None:
    from matplotlib import font_manager as fm

    available = {f.name for f in fm.fontManager.ttflist}
    for name in _KOREAN_FONTS:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지


def concentration_chart(df: pd.DataFrame, path: str | Path, top: int = 10) -> Path | None:
    """종목별 비중(거래금액 기준) 가로 막대 차트."""
    amt = df.groupby("종목명")["거래금액"].sum().sort_values(ascending=False)
    total = float(amt.sum())
    if total <= 0:
        return None

    amt = amt.head(top)
    shares = amt / total * 100

    _apply_korean_font()
    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * len(amt))))
    ax.barh(amt.index[::-1], shares.values[::-1], color="#f5a623")
    ax.set_xlabel("비중 (%)")
    ax.set_title(f"종목별 거래 비중 (상위 {len(amt)})")
    for i, v in enumerate(shares.values[::-1]):
        ax.text(v, i, f" {v:.1f}%", va="center", fontsize=9)
    fig.tight_layout()
    return _save(fig, path)


def trading_distribution_chart(df: pd.DataFrame, path: str | Path) -> Path | None:
    """거래 시간대(시각 또는 요일) 분포 막대 차트."""
    tr = _trading_pattern(df)
    dist = tr.get("distribution", {})
    if not dist:
        return None

    labels = [str(k) for k in dist.keys()]
    values = list(dist.values())
    kind = "시각대" if tr.get("distribution_kind") == "hour" else "요일"

    _apply_korean_font()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values, color="#4a90d9")
    ax.set_ylabel("체결 수")
    ax.set_title(f"거래 {kind}별 분포")
    fig.tight_layout()
    return _save(fig, path)


def pnl_histogram(df: pd.DataFrame, path: str | Path, bins: int = 30) -> Path | None:
    """실현손익 분포 히스토그램. ``실현손익`` 컬럼이 없거나 실현 건이 없으면 None."""
    if "실현손익" not in df.columns:
        return None
    pnl = pd.to_numeric(df["실현손익"], errors="coerce").fillna(0)
    realized = pnl[(pnl != 0) & (df["매매구분"] == SELL)]
    if realized.empty:
        return None

    _apply_korean_font()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(realized.values, bins=bins, color="#7ed321", edgecolor="white")
    ax.axvline(0, color="#d0021b", linewidth=1, linestyle="--")
    ax.set_xlabel("실현손익")
    ax.set_ylabel("체결 수")
    ax.set_title("실현손익 분포")
    fig.tight_layout()
    return _save(fig, path)


def save_all(df: pd.DataFrame, outdir: str | Path) -> list[Path]:
    """가능한 모든 차트를 ``outdir`` 에 저장하고 생성된 경로 목록을 반환한다."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = [
        (concentration_chart, "concentration.png"),
        (trading_distribution_chart, "trading_distribution.png"),
        (pnl_histogram, "pnl_histogram.png"),
    ]
    saved: list[Path] = []
    for fn, name in jobs:
        p = fn(df, outdir / name)
        if p is not None:
            saved.append(p)
    return saved


def _save(fig, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
