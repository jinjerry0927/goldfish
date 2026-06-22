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
    version: Optional[bool] = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True,
        help="버전 출력 후 종료",
    ),
) -> None:
    """CSV 를 읽어 기본 분석 결과를 텍스트로 출력한다."""
    try:
        df = load_csv(csv_path)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    result = analyze_basic(df)
    typer.echo(render_text(result))

    # 금융 거래내역 스키마면 특화 진단도 함께 출력
    if is_finance_df(df):
        typer.echo("")
        typer.echo(render_finance(analyze_finance(df)))


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


def main() -> None:
    _force_utf8_stdio()
    # 인자 없이 호출되면 도움말 출력
    if len(sys.argv) == 1:
        app(["--help"])
    else:
        app()


if __name__ == "__main__":
    main()
