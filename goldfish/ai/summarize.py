"""분석 결과(dict) → 프롬프트 구성 → Gemini 호출 → 자연어 요약.

설계 원칙
---------
* **기본 끔**: 키가 없으면 조용히 건너뛴다(통계만). 크래시 금지.
* **선택 의존성**: ``google-genai`` 는 ``pip install 'goldfish[ai]'`` 일 때만 필요.
  미설치 상태에서도 이 모듈은 import 되어야 하므로 SDK import 는 호출 시점까지 미룬다.
* **가드레일**: 시스템 프롬프트로 "진단·설명만, 투자 추천 금지"를 강제한다.
* **테스트 가능**: 실제 네트워크 호출은 ``_call_gemini`` 한 곳에 격리한다
  (테스트는 이 함수만 monkeypatch).

⚠️ 진단·설명용이며 투자 추천이 아니다.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

ENV_KEY = "GEMINI_API_KEY"
DEFAULT_MODEL = "gemini-2.0-flash"

# 가드레일 시스템 프롬프트 — 투자자문/추천을 금지하고 진단·설명에 한정한다.
SYSTEM_GUARDRAIL = (
    "당신은 개인 투자자의 '거래내역 데이터'를 해설하는 데이터 분석 도우미입니다.\n"
    "아래 규칙을 반드시 지키세요:\n"
    "1) 제공된 분석 수치를 사람이 이해하기 쉬운 한국어로 '설명'만 합니다.\n"
    "2) 매수/매도/보유 등 어떤 형태의 투자 '추천·조언·예측'도 하지 않습니다.\n"
    "   ('지금 사세요/파세요', '오를 것이다' 같은 표현 금지)\n"
    "3) 특정 종목의 미래 가격이나 적정가를 단정하지 않습니다.\n"
    "4) 데이터에 없는 사실을 지어내지 않습니다. 수치는 제공된 값만 사용합니다.\n"
    "5) 위험 신호(과도한 집중·과매매·큰 손실 편향 등)는 '관찰된 패턴'으로서 중립적으로 짚어줍니다.\n"
    "6) 마지막에 '※ 본 요약은 데이터 설명이며 투자 추천이 아닙니다.' 한 줄을 덧붙입니다.\n"
    "분량은 한국어 5~8문장 정도로 간결하게 작성하세요."
)


class AIUnavailable(RuntimeError):
    """AI 요약을 만들 수 없는 상태(키 없음·라이브러리 미설치 등)."""


def _resolve_api_key(api_key: Optional[str]) -> Optional[str]:
    """명시 키 > 환경변수 순으로 API 키를 찾는다. ``.env`` 는 있으면 로드 시도."""
    if api_key:
        return api_key
    # python-dotenv 가 설치돼 있으면 .env 를 환경에 반영(없으면 무시).
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    key = os.environ.get(ENV_KEY, "").strip()
    return key or None


def unavailable_reason(api_key: Optional[str] = None) -> Optional[str]:
    """AI 를 쓸 수 없는 이유를 사람이 읽을 문자열로 반환. 사용 가능하면 ``None``."""
    if _resolve_api_key(api_key) is None:
        return f"{ENV_KEY} 가 설정되지 않았습니다 (.env 또는 환경변수)."
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return "google-genai 미설치: pip install 'goldfish[ai]'"
    return None


def available(api_key: Optional[str] = None) -> bool:
    """키와 라이브러리가 모두 준비됐으면 ``True``."""
    return unavailable_reason(api_key) is None


def _jsonify(obj: Any) -> str:
    """분석 결과 dict 를 프롬프트에 넣기 좋은 JSON 문자열로. NaN 등은 안전 변환."""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def build_prompt(
    basic: dict[str, Any],
    finance: Optional[dict[str, Any]] = None,
) -> str:
    """분석 결과 dict 들을 LLM 입력 프롬프트(사용자 메시지)로 구성한다.

    Args:
        basic: ``analyze_basic`` 결과.
        finance: ``analyze_finance`` 결과(금융 스키마일 때만). 없으면 생략.
    """
    parts: list[str] = [
        "다음은 한 개인의 거래/투자 데이터 분석 수치(JSON)입니다.",
        "이 수치만 근거로, 규칙을 지켜 한국어로 해설해 주세요.",
        "",
        "## 기본 통계 분석",
        "```json",
        _jsonify(basic),
        "```",
    ]
    if finance:
        parts += [
            "",
            "## 금융 특화 진단",
            "```json",
            _jsonify(finance),
            "```",
        ]
    parts += [
        "",
        "요청: 위 데이터에서 눈에 띄는 패턴과 주의해서 볼 만한 신호를 "
        "중립적으로 짚어 설명해 주세요. (추천·예측 금지)",
    ]
    return "\n".join(parts)


def _call_gemini(prompt: str, api_key: str, model: str) -> str:
    """실제 Gemini 호출 — 네트워크 의존부를 한 곳에 격리(테스트는 이 함수만 대체).

    ``google-genai`` SDK 를 호출 시점에 import 한다(선택 의존성).
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_GUARDRAIL,
            temperature=0.4,
        ),
    )
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise AIUnavailable("Gemini 응답이 비어 있습니다.")
    return text


def summarize(
    basic: dict[str, Any],
    finance: Optional[dict[str, Any]] = None,
    *,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """분석 결과를 Gemini 로 자연어 요약해 반환한다.

    Raises:
        AIUnavailable: 키가 없거나 ``google-genai`` 가 설치되지 않은 경우.
            (호출 측에서 잡아 통계만 출력하는 fallback 을 구현한다.)
    """
    reason = unavailable_reason(api_key)
    if reason is not None:
        raise AIUnavailable(reason)
    key = _resolve_api_key(api_key)
    assert key is not None  # unavailable_reason 통과 → 키 존재 보장
    prompt = build_prompt(basic, finance)
    return _call_gemini(prompt, key, model)
