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


def render_finance(result: dict[str, Any]) -> str:
    """``analyze_finance`` 결과를 사람이 읽기 좋은 텍스트로 변환한다."""
    lines: list[str] = []
    add = lines.append

    add("=" * 52)
    add("🐠 GoldFish 금융 특화 진단")
    add("=" * 52)

    conc = result.get("concentration", {})
    add("")
    add("[ 포트폴리오 집중도 ]")
    if conc.get("stocks"):
        add(f"  거래 종목 수: {conc['stocks']}개")
        add(
            f"  최다 비중 종목: {_fmt(conc['top1_share'])}% "
            f"/ 상위 {conc['top_n']}종목: {_fmt(conc['top_n_share'])}%"
        )
        add(f"  HHI(집중지수, 1=완전집중): {conc['hhi']}")
        add("  · 종목별 비중(거래금액 기준)")
        for s in conc.get("by_stock", [])[:5]:
            add(f"      {s['name']}: {_fmt(s['share'])}%")
    else:
        add("  계산할 거래금액 데이터 없음")

    tr = result.get("trading", {})
    add("")
    add("[ 매매 패턴 ]")
    if tr:
        ratio = tr.get("buy_sell_ratio")
        ratio_txt = f"{ratio}" if ratio is not None else "—"
        add(f"  매수 {tr['buy_count']:,}회 / 매도 {tr['sell_count']:,}회 (매수:매도 {ratio_txt})")
        add(
            f"  거래일 {tr['active_days']:,}일 / 총 {tr['total_trades']:,}체결 "
            f"→ 거래일당 {_fmt(tr['trades_per_active_day'])}체결 "
            f"(하루 최대 {tr['max_trades_in_a_day']:,})"
        )
        kind = "시각대" if tr.get("distribution_kind") == "hour" else "요일"
        dist = tr.get("distribution", {})
        if dist:
            body = " ".join(f"{k}:{v}" for k, v in dist.items())
            add(f"  거래 {kind} 분포: {body}")
    else:
        add("  매매 데이터 없음")

    pnl = result.get("pnl")
    add("")
    add("[ 손절·익절 습관 (실현손익) ]")
    if pnl and pnl.get("realized_trades"):
        add(
            f"  실현 {pnl['realized_trades']:,}건 "
            f"(익절 {pnl['wins']:,} / 손절 {pnl['losses']:,}) "
            f"→ 승률 {_fmt(pnl['win_rate'])}%"
        )
        add(f"  총 실현손익: {_fmt(pnl['total_pnl'])}")
        add(f"  평균 익절 {_fmt(pnl['avg_win'])} / 평균 손절 {_fmt(pnl['avg_loss'])}")
        pf = pnl.get("profit_factor")
        add(f"  손익비(Profit Factor): {pf if pf is not None else '—'}")
        add(f"  최대 익절 {_fmt(pnl['biggest_win'])} / 최대 손절 {_fmt(pnl['biggest_loss'])}")
    elif pnl is None:
        add("  실현손익 컬럼 없음 (건너뜀)")
    else:
        add("  실현된 손익 없음")

    ret = result.get("returns")
    add("")
    add("[ 수익률·변동성 (실현손익 기반 추정) ]")
    if ret and ret.get("sell_trades"):
        add(f"  실현 수익률: {_fmt(ret['realized_return_pct'])}% (원가 대비)")
        add(
            f"  체결별 평균 수익률 {_fmt(ret['avg_trade_return_pct'])}% "
            f"/ 변동성(표준편차) {_fmt(ret['return_volatility_pct'])}%"
        )
    elif ret is None:
        add("  실현손익 컬럼 없음 (건너뜀)")
    else:
        add("  매도 체결 없음")

    add("")
    add("=" * 52)
    add("ℹ️  본 진단은 데이터 설명용이며 투자 추천이 아닙니다.")
    add("=" * 52)

    return "\n".join(lines)
