"""AI 요약 계층 테스트 — 실제 네트워크/SDK 없이 mock 으로 검증.

google-genai 가 설치돼 있지 않은 환경에서도 통과해야 한다(선택 의존성).
실제 Gemini 호출(``_call_gemini``)과 가용성 판단(``unavailable_reason``)만
monkeypatch 하고, 나머지 로직(프롬프트 구성·fallback)은 진짜로 실행한다.
"""
from __future__ import annotations

import pandas as pd

import importlib

import goldfish.ai as ai_pkg

# 주의: ``goldfish.ai`` 패키지가 동명의 함수 ``summarize`` 를 재노출하므로
# ``import goldfish.ai.summarize as m`` 는 (함수로) 가려진다. 진짜 모듈 객체는
# sys.modules 에서 가져온다(monkeypatch 대상이 모듈 속성이라 필요).
ai_mod = importlib.import_module("goldfish.ai.summarize")
from goldfish.analyzers.basic import analyze_basic
from goldfish.analyzers.finance import analyze_finance
from goldfish.report.summary import summary


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


def _analyses():
    df = _trades_df()
    return analyze_basic(df), analyze_finance(df)


# --- 프롬프트 구성 ----------------------------------------------------------

def test_build_prompt_includes_both_analyses():
    basic, finance = _analyses()
    prompt = ai_mod.build_prompt(basic, finance)
    assert "기본 통계 분석" in prompt
    assert "금융 특화 진단" in prompt
    # 분석 수치가 실제로 프롬프트 안에 직렬화돼 들어갔는지
    assert "가나전자" in prompt
    assert "추천·예측 금지" in prompt


def test_build_prompt_without_finance_omits_section():
    basic, _ = _analyses()
    prompt = ai_mod.build_prompt(basic, None)
    assert "기본 통계 분석" in prompt
    assert "금융 특화 진단" not in prompt


def test_guardrail_forbids_recommendation():
    # 시스템 프롬프트가 추천 금지·면책을 명시하는지
    assert "추천" in ai_mod.SYSTEM_GUARDRAIL
    assert "투자 추천이 아닙니다" in ai_mod.SYSTEM_GUARDRAIL


# --- 가용성/ fallback -------------------------------------------------------

def _force_no_key(monkeypatch):
    """키 없는 상태를 보장 — 환경변수 제거 + 실제 .env 의 load_dotenv 무력화."""
    monkeypatch.delenv(ai_mod.ENV_KEY, raising=False)
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)


def test_unavailable_when_no_key(monkeypatch):
    _force_no_key(monkeypatch)
    reason = ai_mod.unavailable_reason(api_key=None)
    assert reason is not None
    assert ai_mod.ENV_KEY in reason
    assert ai_mod.available(api_key=None) is False


def test_summarize_raises_when_unavailable(monkeypatch):
    _force_no_key(monkeypatch)
    basic, finance = _analyses()
    try:
        ai_mod.summarize(basic, finance, api_key=None)
    except ai_mod.AIUnavailable:
        pass
    else:  # pragma: no cover
        raise AssertionError("키 없을 때 AIUnavailable 가 발생해야 한다")


def test_report_summary_returns_none_when_unavailable(monkeypatch):
    _force_no_key(monkeypatch)
    assert summary(_trades_df(), api_key=None) is None


# --- 성공 경로(호출 mock) ---------------------------------------------------

def test_summarize_calls_gemini_with_prompt(monkeypatch):
    captured = {}

    def fake_call(prompt, api_key, model):
        captured["prompt"] = prompt
        captured["api_key"] = api_key
        captured["model"] = model
        return "관찰된 패턴 요약입니다. ※ 본 요약은 데이터 설명이며 투자 추천이 아닙니다."

    # 라이브러리 미설치 환경에서도 성공 경로를 타도록 가용성 판단을 통과시킨다.
    monkeypatch.setattr(ai_mod, "unavailable_reason", lambda api_key=None: None)
    monkeypatch.setattr(ai_mod, "_call_gemini", fake_call)

    basic, finance = _analyses()
    out = ai_mod.summarize(basic, finance, api_key="dummy-key", model="gemini-test")
    assert "투자 추천이 아닙니다" in out
    assert captured["api_key"] == "dummy-key"
    assert captured["model"] == "gemini-test"
    assert "기본 통계 분석" in captured["prompt"]


def test_report_summary_uses_ai(monkeypatch):
    monkeypatch.setattr(ai_pkg, "available", lambda api_key=None: True)
    monkeypatch.setattr(ai_pkg, "summarize", lambda *a, **k: "AI 요약 텍스트")
    out = summary(_trades_df(), api_key="dummy-key")
    assert out == "AI 요약 텍스트"


class _FakeAPIError(Exception):
    """genai APIError 흉내 — status/code 속성만 갖는다."""

    def __init__(self, status="", code=None, message=""):
        super().__init__(message or status)
        self.status = status
        self.code = code
        self.message = message


def test_friendly_api_error_quota():
    msg = ai_mod._friendly_api_error(_FakeAPIError(status="RESOURCE_EXHAUSTED"))
    assert "한도 초과" in msg


def test_friendly_api_error_auth():
    msg = ai_mod._friendly_api_error(_FakeAPIError(status="PERMISSION_DENIED"))
    assert "인증 실패" in msg


def test_friendly_api_error_other_is_single_line():
    msg = ai_mod._friendly_api_error(_FakeAPIError(message="boom\n세부정보\n더보기"))
    assert "\n" not in msg
    assert "boom" in msg
