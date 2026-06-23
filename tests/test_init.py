"""goldfish init 워크스페이스 스캐폴딩 + CLI 라우팅 테스트."""
from __future__ import annotations

from goldfish.cli import _SUBCOMMANDS, _run_folder
from goldfish.workspace import init_workspace


def test_init_creates_structure(tmp_path):
    ws = init_workspace(tmp_path / "작업폴더")
    assert (ws / "_템플릿").is_dir()
    assert (ws / "리포트").is_dir()
    assert (ws / "사용법.txt").exists()
    assert (ws / "리포트_만들기.bat").exists()
    assert (ws / "run.command").exists()
    assert (ws / "_템플릿" / "거래내역_템플릿.csv").exists()


def test_init_is_idempotent_and_keeps_user_edits(tmp_path):
    ws = init_workspace(tmp_path / "ws")
    csv = ws / "_템플릿" / "거래내역_템플릿.csv"
    csv.write_text("사용자수정", encoding="utf-8")
    init_workspace(tmp_path / "ws")  # 다시 실행해도 기존 파일 보존
    assert csv.read_text(encoding="utf-8") == "사용자수정"


def test_csv_template_is_finance_schema(tmp_path):
    from goldfish.analyzers.finance import is_finance_df
    from goldfish.loaders.csv import load_csv

    ws = init_workspace(tmp_path / "ws")
    df = load_csv(ws / "_템플릿" / "거래내역_템플릿.csv")
    assert is_finance_df(df)  # 양식이 금융 스키마로 인식돼야 함


def test_run_folder_generates_reports(tmp_path):
    ws = init_workspace(tmp_path / "ws")
    (ws / "거래.csv").write_text(
        "체결일,종목명,매매구분,수량,단가,거래금액,종목코드,실현손익\n"
        "2026-01-15,삼성전자,매수,10,72000,720000,005930,0\n"
        "2026-02-03,삼성전자,매도,10,75000,750000,005930,30000\n",
        encoding="utf-8",
    )
    _run_folder(ws)
    assert (ws / "리포트" / "거래_리포트.html").exists()


def test_subcommands_registered():
    assert {"analyze", "init"} <= _SUBCOMMANDS
