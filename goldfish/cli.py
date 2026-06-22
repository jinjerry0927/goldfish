"""goldfish CLI — ``goldfish <csv경로>`` → 텍스트 분석 리포트."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from goldfish import __version__
from goldfish.analyzers.basic import analyze_basic
from goldfish.loaders.csv import load_csv
from goldfish.report.text import render_text

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


def main() -> None:
    # 인자 없이 호출되면 도움말 출력
    if len(sys.argv) == 1:
        app(["--help"])
    else:
        app()


if __name__ == "__main__":
    main()
