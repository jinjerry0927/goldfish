"""HTML 리포트 테스트 — 구조/내용 위주(시각 정확성은 검증 안 함).

matplotlib 가 없어도 통과해야 한다(차트는 선택 의존성 → 없으면 조용히 생략).
"""
from __future__ import annotations

import pandas as pd

from goldfish.report import html as html_mod


def _trades_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "체결일": ["2025-06-02", "2025-06-03", "2025-06-04"],
            "종목명": ["가나전자", "가나전자", "다라반도체"],
            "매매구분": ["매수", "매도", "매도"],
            "수량": [10, 5, 8],
            "단가": [100.0, 120.0, 250.0],
            "거래금액": [1000, 600, 2000],
            "실현손익": [0, 100, 400],
        }
    )


def _plain_df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})


def test_render_html_is_self_contained_document():
    out = html_mod.render_html(_trades_df(), charts=False)
    assert out.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in out.rstrip()
    assert "🐠" in out
    # 면책 문구가 포함돼야 한다
    assert "투자 추천이 아닙니다" in out


def test_render_html_includes_finance_section_for_trades():
    out = html_mod.render_html(_trades_df(), charts=False)
    assert "기본 통계 분석" in out
    assert "금융 특화 진단" in out
    assert "포트폴리오 집중도" in out
    assert "가나전자" in out


def test_render_html_omits_finance_for_plain_data():
    out = html_mod.render_html(_plain_df(), charts=False)
    assert "기본 통계 분석" in out
    assert "금융 특화 진단" not in out


def test_render_html_includes_ai_summary_when_given():
    out = html_mod.render_html(
        _trades_df(), charts=False, ai_summary="관찰된 패턴 요약입니다."
    )
    assert "AI 코칭 요약" in out
    assert "관찰된 패턴 요약입니다." in out


def test_render_html_omits_ai_section_when_absent():
    out = html_mod.render_html(_trades_df(), charts=False)
    assert "AI 코칭 요약" not in out


def test_html_escapes_values(monkeypatch):
    df = _trades_df().copy()
    df.loc[0, "종목명"] = "<script>x</script>"
    out = html_mod.render_html(df, charts=False)
    assert "<script>x</script>" not in out
    assert "&lt;script&gt;" in out


def test_to_html_writes_utf8_file(tmp_path):
    path = html_mod.to_html(_trades_df(), tmp_path / "report.html", charts=False)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "🐠" in content


def test_charts_embedded_as_base64_when_available(tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("matplotlib")
    out = html_mod.render_html(_trades_df(), charts=True)
    # 차트는 외부 파일이 아닌 인라인 data URI 로 임베드돼야 한다
    assert "data:image/png;base64," in out
    assert "📈 차트" in out
