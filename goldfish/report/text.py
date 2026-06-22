"""기본 분석 결과(dict) → 보기 좋은 텍스트 리포트."""
from __future__ import annotations

from typing import Any


def _fmt(n: float) -> str:
    """수치를 천단위 구분 + 소수 2자리 이내로 표기."""
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.2f}"
    return f"{int(n):,}"


def render_text(result: dict[str, Any]) -> str:
    """``analyze_basic`` 결과를 사람이 읽기 좋은 텍스트로 변환한다."""
    lines: list[str] = []
    add = lines.append

    add("=" * 52)
    add("🐠 GoldFish 기본 분석 리포트")
    add("=" * 52)

    ov = result.get("overview", {})
    add("")
    add(f"[ 개요 ]  {ov.get('rows', 0):,}행 × {ov.get('cols', 0)}열")
    for col, dtype in ov.get("dtypes", {}).items():
        add(f"  - {col}: {dtype}")

    missing = result.get("missing", {})
    add("")
    add("[ 결측치 ]")
    if missing:
        for col, info in missing.items():
            add(f"  - {col}: {info['count']:,}개 ({info['pct']}%)")
    else:
        add("  없음 ✅")

    dist = result.get("distribution", {})
    add("")
    add("[ 수치형 분포 ]")
    if dist:
        for col, st in dist.items():
            add(f"  · {col}")
            add(
                f"      평균 {_fmt(st['mean'])} / 중앙 {_fmt(st['median'])} "
                f"/ 표준편차 {_fmt(st['std'])}"
            )
            add(
                f"      min {_fmt(st['min'])} | Q1 {_fmt(st['q25'])} "
                f"| Q3 {_fmt(st['q75'])} | max {_fmt(st['max'])}"
            )
    else:
        add("  수치형 컬럼 없음")

    outliers = result.get("outliers", {})
    add("")
    add("[ 이상치 (IQR 1.5배) ]")
    if outliers:
        for col, info in outliers.items():
            add(
                f"  - {col}: {info['count']:,}개 ({info['pct']}%) "
                f"[정상범위 {_fmt(info['lower'])} ~ {_fmt(info['upper'])}]"
            )
    else:
        add("  없음 ✅")

    corr = result.get("correlation", {})
    top = corr.get("top_pairs", [])
    add("")
    add("[ 상관관계 상위 ]")
    if top:
        for p in top:
            add(f"  - {p['a']} ↔ {p['b']}: {p['corr']:+.3f}")
    else:
        add("  계산 가능한 수치형 페어 없음")

    add("")
    add("=" * 52)
    add("ℹ️  본 리포트는 데이터 진단·설명용이며 투자 추천이 아닙니다.")
    add("=" * 52)

    return "\n".join(lines)
