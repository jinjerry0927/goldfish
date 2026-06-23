"""goldfish CLI — ``goldfish <csv경로>`` → 텍스트 분석 리포트."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from goldfish import __version__
from goldfish.analyzers.basic import analyze_basic
from goldfish.analyzers.finance import analyze_finance, is_finance_df
from goldfish.loaders.csv import load_csv
from goldfish.report.text import render_finance, render_text


def _force_utf8_stdio() -> None:
    """이모지·한글 출력이 콘솔 기본 인코딩(예: Windows cp949)에서 깨지지 않도록
    stdout/stderr 를 UTF-8 로 재설정한다. 지원하지 않는 환경이면 조용히 넘어간다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

app = typer.Typer(
    add_completion=False,
    help="🐠 GoldFish — 내 투자·거래 데이터를 어항 들여다보듯 분석.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"goldfish {__version__}")
        raise typer.Exit()


@app.command()
def analyze(
    csv_path: Path = typer.Argument(..., help="분석할 CSV 파일 경로"),
    charts: Optional[Path] = typer.Option(
        None, "--charts", help="차트 PNG 를 저장할 디렉터리 (금융 데이터일 때만)",
    ),
    html: Optional[Path] = typer.Option(
        None, "--html", help="분석 결과를 HTML 리포트 한 장으로 저장할 경로",
    ),
    ai: bool = typer.Option(
        False, "--ai", help="AI 자연어 요약 추가 (GEMINI_API_KEY 필요, 기본 끔)",
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True,
        help="버전 출력 후 종료",
    ),
) -> None:
    """CSV 를 읽어 기본 분석 결과를 텍스트로 출력한다."""
    _force_utf8_stdio()
    try:
        df = load_csv(csv_path)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    result = analyze_basic(df)
    typer.echo(render_text(result))

    # 금융 거래내역 스키마면 특화 진단도 함께 출력
    finance_df = is_finance_df(df)
    if finance_df:
        typer.echo("")
        typer.echo(render_finance(analyze_finance(df)))

    if charts is not None:
        if not finance_df:
            typer.secho(
                "차트는 금융 거래내역 스키마에서만 생성됩니다 (건너뜀).",
                fg=typer.colors.YELLOW, err=True,
            )
        else:
            try:
                from goldfish.report.charts import save_all
            except ImportError:
                typer.secho(
                    "matplotlib 가 필요합니다: pip install 'goldfish[charts]'",
                    fg=typer.colors.RED, err=True,
                )
                raise typer.Exit(code=1)
            saved = save_all(df, charts)
            typer.echo("")
            typer.echo(f"📊 차트 {len(saved)}개 저장:")
            for p in saved:
                typer.echo(f"  - {p}")

    ai_text: Optional[str] = None
    if ai:
        from goldfish import ai as ai_mod
        from goldfish.report.summary import summary

        reason = ai_mod.unavailable_reason()
        if reason is not None:
            typer.secho(f"AI 요약 건너뜀 — {reason}", fg=typer.colors.YELLOW, err=True)
        else:
            try:
                ai_text = summary(df)
            except ai_mod.AIUnavailable as e:
                typer.secho(f"AI 요약 실패 — {e}", fg=typer.colors.RED, err=True)
            else:
                typer.echo("")
                typer.echo("=" * 52)
                typer.echo("🤖 GoldFish AI 코칭 요약")
                typer.echo("=" * 52)
                typer.echo("")
                typer.echo(ai_text)

    if html is not None:
        from goldfish.report.html import to_html

        # --ai 로 만든 요약이 있으면 HTML 에도 함께 싣는다.
        saved_html = to_html(df, html, ai_summary=ai_text)
        typer.echo("")
        typer.echo(f"📄 HTML 리포트 저장: {saved_html}")


def main() -> None:
    _force_utf8_stdio()
    # 인자 없이 호출되면 도움말 출력
    if len(sys.argv) == 1:
        app(["--help"])
    else:
        app()


if __name__ == "__main__":
    main()
