# 🐠 GoldFish

> 내 투자·거래 데이터를 어항 들여다보듯 분석해주는 도구
>
> **Watch your money swim.**

CSV(추후 토스증권 조회 API)로 투자·거래 데이터를 넣으면 **통계 프로파일링 + 금융 특화 진단 + AI 자연어 코칭**을 담은 리포트를 만들어 주는 Python 라이브러리/CLI입니다.

기존 범용 프로파일링 도구와 달리 **금융 데이터에 특화**되어 있고, 분석 결과를 AI가 사람 말로 해설·경고해 주는 것이 차별점입니다.

---

## ✨ 기능 (v0.1)

- 📥 **CSV 로더** — 한글/BOM/`cp949` 자동 처리
- 📊 **기본 프로파일링** — 행·열 수, 결측치, 데이터 타입, 분포(평균/중앙/표준편차/분위)
- 🔎 **이상치 탐지** — IQR(1.5배) 기준
- 🔗 **상관관계** — 수치형 컬럼 간 상관계수 상위 페어
- 🖥 **CLI** — `goldfish <csv경로>` 한 줄로 텍스트 리포트

> 로드맵: v0.2 금융 특화 진단·차트 · v0.3 AI 코칭 · v0.4 토스 연동·HTML 리포트 · v1.0 PyPI 배포

---

## 📦 설치

```bash
git clone https://github.com/jinuk-james-lee/goldfish.git
cd goldfish
pip install -e .
```

> Python 3.10+ 필요. (PyPI 배포는 v1.0 예정)

---

## 🚀 사용 예시

```bash
# 샘플 합성 데이터 생성
python examples/generate_sample.py

# 분석 리포트 출력
goldfish examples/sample.csv
```

라이브러리로도 사용할 수 있습니다:

```python
from goldfish.loaders.csv import load_csv
from goldfish.analyzers.basic import analyze_basic
from goldfish.report.text import render_text

df = load_csv("examples/sample.csv")
result = analyze_basic(df)   # dict — 텍스트/HTML/AI 계층에서 재사용
print(render_text(result))
```

출력 예시:

```
====================================================
🐠 GoldFish 기본 분석 리포트
====================================================

[ 개요 ]  500행 × 8열
  ...
[ 이상치 (IQR 1.5배) ]
  - 거래금액: 54개 (10.8%) ...
[ 상관관계 상위 ]
  - 단가 ↔ 거래금액: +0.768
```

---

## 🧪 개발

```bash
pip install -e ".[dev]"
pytest
```

---

## ⚠️ 면책 / 안전 원칙

- 본 도구는 **데이터 진단·설명용**이며, **투자 추천·자문이 아닙니다.** 투자 판단의 책임은 사용자 본인에게 있습니다.
- 토스증권 연동(v0.4 예정)은 **조회(read-only) 전용**입니다 — 주문/매매 기능은 제공하지 않습니다.
- API 키는 반드시 `.env`에만 보관하세요 (`.env.example` 참고). 저장소에 커밋 금지.
- 저장소의 샘플 데이터는 **100% 합성 데이터**이며 실제 거래 정보가 아닙니다.
- "토스"는 해당 사 상표이며, 본 프로젝트는 **비공식** 연동 도구입니다.

---

## 📄 라이선스

[MIT](LICENSE) © 2026 James Lee
