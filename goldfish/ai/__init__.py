"""AI 계층 — 분석 결과(dict)를 LLM(Gemini)이 사람 말로 해설·경고.

기본값은 **AI 끔**이다. 키(`GEMINI_API_KEY`)가 없거나 `google-genai` 가
설치돼 있지 않으면 이 계층은 그냥 건너뛰며, 통계 분석만 출력된다.

⚠️ LLM 출력도 진단·설명용이며 투자 추천이 아니다(프롬프트 가드레일로 강제).
"""

from goldfish.ai.summarize import (
    AIUnavailable,
    available,
    build_prompt,
    summarize,
    unavailable_reason,
)

__all__ = [
    "AIUnavailable",
    "available",
    "build_prompt",
    "summarize",
    "unavailable_reason",
]
