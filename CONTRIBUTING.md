# 🐠 기여 가이드 (Contributing)

GoldFish에 관심 가져주셔서 감사합니다! 이 프로젝트는 **내 투자·거래 데이터를
어항 들여다보듯 분석**해주는 도구입니다. 작은 수정부터 새 분석 기능까지 환영합니다.

> 배포명은 `goldfish-finance`, 코드 import 패키지명은 `goldfish` 입니다.

## 🚦 시작하기 전에 — 프로젝트 상시 원칙

이 원칙은 **반드시** 지켜주세요 (PR 리뷰의 기준입니다):

1. **토스 API는 조회(read-only)만** — 주문/매매(생성·정정·취소) 코드는 절대 추가하지 않습니다.
2. **자격증명은 `.env`에만** — 키/시크릿을 코드·테스트·커밋에 하드코딩 금지. 커밋 전 `git status`로 `.env` 미포함 확인.
3. **"추천"이 아니라 "진단·설명"** — 투자자문이 아닙니다. 면책 문구와 가드레일을 유지하세요.
4. **`analyzers`는 AI/토스 없이도 동작** — 외부 의존성 없이 통계 분석이 항상 가능해야 합니다.

## 🛠 개발 환경

```bash
git clone https://github.com/jinjerry0927/goldfish.git
cd goldfish
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,charts,toss,ai]"              # 전체 extra 설치(테스트 전부 실행용)
```

Python 3.10+ 가 필요합니다.

## 🧪 테스트

PR을 올리기 전에 전체 테스트가 통과하는지 확인하세요. CI(GitHub Actions)도
Python 3.10~3.13에서 동일하게 검증합니다.

```bash
pytest -q
```

- 새 기능/버그 수정에는 **테스트를 함께** 추가해주세요.
- 외부 호출(토스 API·Gemini)은 **반드시 mock**으로 — 실제 네트워크/자격증명 없이 통과해야 합니다.
- 차트 테스트는 `matplotlib`가 없으면 자동으로 skip 됩니다.

## 📁 코드 구조

| 디렉터리 | 역할 |
|---|---|
| `goldfish/loaders/` | 데이터 입력 (CSV, 토스 조회) |
| `goldfish/analyzers/` | 분석 로직 (basic 통계 · finance 금융진단) — **외부 의존성 없이 동작** |
| `goldfish/report/` | 출력 (text · charts · html · summary) |
| `goldfish/ai/` | AI 요약 계층 (선택, 기본 꺼짐) |
| `tests/` | pytest |
| `examples/` | 합성 샘플 데이터 (개인정보 無) |

## 🔀 PR 가이드

- 한 PR = 한 가지 목적. 가능하면 작게 나눠주세요.
- 커밋 메시지는 가급적 `feat:` / `fix:` / `docs:` / `chore:` 접두어를 사용해주세요.
- PR 설명에 **무엇을·왜** 바꿨는지, 상시 원칙(특히 read-only)을 어기지 않았는지 적어주세요.

## 🐞 버그·기능 제안

[이슈](https://github.com/jinjerry0927/goldfish/issues)로 남겨주세요. 버그 리포트에는
재현 방법과 환경(OS·Python 버전)을, 기능 제안에는 해결하려는 문제를 함께 적어주시면 좋습니다.

감사합니다! 🐠
