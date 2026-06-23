"""HTML 리포트 — 분석 결과(기본+금융) + 차트 + AI 요약을 한 장의 HTML 로.

설계 원칙
---------
* **자기완결(self-contained)**: 차트 PNG 를 base64 로 인라인 임베드해 외부 파일
  의존 없이 HTML 한 장만으로 열린다.
* **점진적 기능**: 금융 스키마가 아니면 금융 섹션을 생략하고, ``matplotlib``
  (선택 의존성)이 없으면 차트를 조용히 건너뛴다. AI 요약도 없으면 생략한다.
* **가드레일**: 텍스트 리포트와 동일하게 "투자 추천이 아님" 면책을 명시한다.

진입점
------
* :func:`render_html` — DataFrame → HTML 문자열.
* :func:`to_html` — DataFrame → HTML 파일로 저장(경로 반환).

⚠️ 진단·설명용이며 투자 추천이 아니다.
"""
from __future__ import annotations

import base64
import html
import tempfile
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from goldfish.analyzers.basic import analyze_basic
from goldfish.analyzers.finance import analyze_finance, is_finance_df

# 금붕어 브랜딩 팔레트 (차트의 #f5a623 골드와 통일)
_GOLD = "#f5a623"
_BLUE = "#4a90d9"
_INK = "#2b2b2b"
_DISCLAIMER = "본 리포트는 데이터 진단·설명용이며 투자 추천이 아닙니다."


def _fmt(n: Any) -> str:
    """수치를 천단위 구분 + 소수 2자리 이내로. 숫자가 아니면 문자열 그대로."""
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        return html.escape(str(n))
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.2f}"
    return f"{int(n):,}"


def _esc(s: Any) -> str:
    return html.escape(str(s))


# --- 섹션 렌더러 (HTML 조각) -------------------------------------------------

def _basic_section(b: dict[str, Any]) -> str:
    ov = b.get("overview", {})
    rows = [f"<p class='kv'>{ov.get('rows', 0):,}행 × {ov.get('cols', 0)}열</p>"]

    missing = b.get("missing", {})
    if missing:
        items = "".join(
            f"<li>{_esc(c)}: {info['count']:,}개 ({info['pct']}%)</li>"
            for c, info in missing.items()
        )
        rows.append(f"<h4>결측치</h4><ul>{items}</ul>")
    else:
        rows.append("<h4>결측치</h4><p class='ok'>없음 ✅</p>")

    dist = b.get("distribution", {})
    if dist:
        body = "".join(
            f"<tr><td>{_esc(c)}</td><td>{_fmt(st['mean'])}</td><td>{_fmt(st['median'])}</td>"
            f"<td>{_fmt(st['std'])}</td><td>{_fmt(st['min'])}</td><td>{_fmt(st['max'])}</td></tr>"
            for c, st in dist.items()
        )
        rows.append(
            "<h4>수치형 분포</h4><table><thead><tr>"
            "<th>컬럼</th><th>평균</th><th>중앙</th><th>표준편차</th><th>min</th><th>max</th>"
            f"</tr></thead><tbody>{body}</tbody></table>"
        )

    corr = b.get("correlation", {}).get("top_pairs", [])
    if corr:
        items = "".join(
            f"<li>{_esc(p['a'])} ↔ {_esc(p['b'])}: {p['corr']:+.3f}</li>" for p in corr
        )
        rows.append(f"<h4>상관관계 상위</h4><ul>{items}</ul>")

    return _card("📊 기본 통계 분석", "".join(rows))


def _finance_section(f: dict[str, Any]) -> str:
    parts: list[str] = []

    conc = f.get("concentration", {})
    if conc.get("stocks"):
        bars = "".join(
            f"<div class='bar-row'><span class='bar-label'>{_esc(s['name'])}</span>"
            f"<span class='bar'><span class='bar-fill' style='width:{min(s['share'], 100):.1f}%'></span></span>"
            f"<span class='bar-val'>{_fmt(s['share'])}%</span></div>"
            for s in conc.get("by_stock", [])[:8]
        )
        parts.append(
            f"<h4>포트폴리오 집중도</h4>"
            f"<p class='kv'>거래 종목 {conc['stocks']}개 · 최다 비중 {_fmt(conc['top1_share'])}% · "
            f"상위 {conc['top_n']}종목 {_fmt(conc['top_n_share'])}% · HHI {conc['hhi']}</p>"
            f"<div class='bars'>{bars}</div>"
        )

    tr = f.get("trading", {})
    if tr:
        ratio = tr.get("buy_sell_ratio")
        parts.append(
            "<h4>매매 패턴</h4>"
            f"<p class='kv'>매수 {tr['buy_count']:,}회 / 매도 {tr['sell_count']:,}회 "
            f"(매수:매도 {ratio if ratio is not None else '—'})</p>"
            f"<p class='kv'>거래일 {tr['active_days']:,}일 · 총 {tr['total_trades']:,}체결 · "
            f"거래일당 {_fmt(tr['trades_per_active_day'])}체결 "
            f"(하루 최대 {tr['max_trades_in_a_day']:,})</p>"
        )

    pnl = f.get("pnl")
    if pnl and pnl.get("realized_trades"):
        pf = pnl.get("profit_factor")
        parts.append(
            "<h4>손절·익절 습관</h4>"
            f"<p class='kv'>실현 {pnl['realized_trades']:,}건 "
            f"(익절 {pnl['wins']:,} / 손절 {pnl['losses']:,}) · 승률 {_fmt(pnl['win_rate'])}%</p>"
            f"<p class='kv'>총 실현손익 {_fmt(pnl['total_pnl'])} · "
            f"평균 익절 {_fmt(pnl['avg_win'])} / 평균 손절 {_fmt(pnl['avg_loss'])} · "
            f"손익비 {pf if pf is not None else '—'}</p>"
        )

    ret = f.get("returns")
    if ret and ret.get("sell_trades"):
        parts.append(
            "<h4>수익률·변동성 (실현손익 기반 추정)</h4>"
            f"<p class='kv'>실현 수익률 {_fmt(ret['realized_return_pct'])}% (원가 대비) · "
            f"체결별 평균 {_fmt(ret['avg_trade_return_pct'])}% · "
            f"변동성 {_fmt(ret['return_volatility_pct'])}%</p>"
        )

    if not parts:
        return ""
    return _card("🐠 금융 특화 진단", "".join(parts))


def _charts_section(df: pd.DataFrame) -> str:
    """차트를 생성해 base64 로 임베드. matplotlib 없거나 그릴 게 없으면 빈 문자열."""
    try:
        from goldfish.report.charts import save_all
    except ImportError:
        return ""

    with tempfile.TemporaryDirectory() as tmp:
        saved = save_all(df, tmp)
        imgs = []
        for p in saved:
            data = base64.b64encode(Path(p).read_bytes()).decode("ascii")
            imgs.append(
                f"<img alt='{_esc(Path(p).stem)}' src='data:image/png;base64,{data}'/>"
            )
    if not imgs:
        return ""
    return _card("📈 차트", f"<div class='charts'>{''.join(imgs)}</div>")


def _ai_section(text: Optional[str]) -> str:
    if not text:
        return ""
    return _card("🤖 AI 코칭 요약", f"<p class='ai'>{_esc(text)}</p>")


def _card(title: str, body: str) -> str:
    return f"<section class='card'><h2>{_esc(title)}</h2>{body}</section>"


# --- 진입점 ------------------------------------------------------------------

def render_html(
    df: pd.DataFrame,
    *,
    title: str = "GoldFish 분석 리포트",
    charts: bool = True,
    ai_summary: Optional[str] = None,
) -> str:
    """DataFrame 을 분석해 자기완결 HTML 문자열로 반환한다.

    Args:
        df: 분석할 DataFrame.
        title: 문서 제목.
        charts: 금융 스키마일 때 차트를 임베드할지 여부(matplotlib 필요).
        ai_summary: 이미 만들어 둔 AI 요약 텍스트(있으면 표시). 없으면 AI 섹션 생략.
            (네트워크 호출은 호출 측 책임 — 이 함수는 순수 렌더링.)
    """
    basic = analyze_basic(df)
    finance = analyze_finance(df) if is_finance_df(df) else None

    sections = [_basic_section(basic)]
    if finance:
        sections.append(_finance_section(finance))
        if charts:
            sections.append(_charts_section(df))
    sections.append(_ai_section(ai_summary))

    body = "\n".join(s for s in sections if s)
    return _DOCUMENT.format(title=_esc(title), body=body, css=_CSS, disclaimer=_esc(_DISCLAIMER))


def to_html(
    df: pd.DataFrame,
    path: str | Path,
    *,
    title: str = "GoldFish 분석 리포트",
    charts: bool = True,
    ai_summary: Optional[str] = None,
) -> Path:
    """:func:`render_html` 결과를 UTF-8 HTML 파일로 저장하고 경로를 반환한다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_html(df, title=title, charts=charts, ai_summary=ai_summary),
        encoding="utf-8",
    )
    return path


_CSS = """
:root{--gold:%s;--blue:%s;--ink:%s;}
*{box-sizing:border-box;}
body{margin:0;padding:2rem 1rem;background:#fbf7ef;color:var(--ink);
  font-family:'Segoe UI','Malgun Gothic',-apple-system,sans-serif;line-height:1.6;}
.wrap{max-width:860px;margin:0 auto;}
header{text-align:center;margin-bottom:1.5rem;}
header h1{margin:.2rem 0;font-size:1.9rem;}
header .sub{color:#8a7a55;font-size:.9rem;}
.card{background:#fff;border:1px solid #efe3c8;border-radius:14px;
  padding:1.2rem 1.4rem;margin:1rem 0;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.card h2{margin:.1rem 0 .8rem;font-size:1.25rem;border-bottom:3px solid var(--gold);
  display:inline-block;padding-bottom:.2rem;}
.card h4{margin:1rem 0 .3rem;color:#6b5a2e;font-size:.95rem;}
.kv{margin:.2rem 0;}
.ok{color:#3a9d3a;}
table{width:100%%;border-collapse:collapse;font-size:.88rem;margin:.3rem 0;}
th,td{padding:.35rem .5rem;text-align:right;border-bottom:1px solid #f0e9d8;}
th:first-child,td:first-child{text-align:left;}
thead th{background:#fdf6e6;color:#6b5a2e;}
ul{margin:.3rem 0;padding-left:1.2rem;}
.bars{margin:.4rem 0;}
.bar-row{display:flex;align-items:center;gap:.6rem;margin:.25rem 0;font-size:.88rem;}
.bar-label{width:30%%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.bar{flex:1;background:#f3ecda;border-radius:6px;height:14px;overflow:hidden;}
.bar-fill{display:block;height:100%%;background:var(--gold);}
.bar-val{width:64px;text-align:right;color:#6b5a2e;}
.charts{display:flex;flex-direction:column;gap:1rem;}
.charts img{width:100%%;border:1px solid #f0e9d8;border-radius:8px;}
.ai{white-space:pre-wrap;background:#fdf6e6;border-radius:8px;padding:.8rem 1rem;}
footer{text-align:center;color:#a89a73;font-size:.82rem;margin-top:1.5rem;}
""" % (_GOLD, _BLUE, _INK)


_DOCUMENT = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>🐠 {title}</h1>
  <div class="sub">내 투자·거래 데이터를 어항 들여다보듯</div>
</header>
{body}
<footer>ℹ️ {disclaimer}</footer>
</div>
</body>
</html>
"""
