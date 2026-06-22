# 🐠 GoldFish — 전체 작업 목록 (Loop 진행용)

> **Loop 규칙**: 위에서부터 미완료(`[ ]`) 항목을 하나 집어 완료하고 `[x]`로 체크한다.
> 한 항목 = 한 루프에서 끝낼 수 있는 단위. 완료 시 짧게 무엇을 했는지 커밋/기록.
> 막히면 그 항목에 `⚠️ 메모`를 남기고 다음으로 넘어가지 말고 사용자에게 보고.

기획서: [docs/기획서.md](docs/기획서.md)

---

## 🟢 v0.1 — 안전한 골격 + 기본 프로파일링 (토스 ❌ / AI ❌)
> 목표: `goldfish examples/sample.csv` → 분석 결과가 텍스트로 출력되는 상태

### 안전 바닥
- [x] `.gitignore` 생성 (`.env`, `*.key`, `__pycache__/`, 빌드 산출물 제외)
- [x] `.env.example` 생성 (값 없이 키 양식만)

### 패키지 골격
- [x] `pyproject.toml` 작성 (이름 `goldfish`, deps: pandas/numpy/typer)
- [x] `goldfish/__init__.py` + 버전 표기
- [x] 폴더 골격 생성 (`loaders/`, `analyzers/`, `report/`, `tests/`, `examples/`)

### 샘플 데이터
- [x] `examples/generate_sample.py` — 합성 거래 데이터 생성 스크립트 (개인정보 無)
- [x] `examples/sample.csv` — 생성된 샘플 (체결일/종목/수량/단가/매수매도 등)

### 기본 분석
- [x] `loaders/csv.py` — `load_csv(path)` 구현
- [x] `analyzers/basic.py` — 행/열 수, 결측치, 데이터 타입, 기초 통계
- [x] `analyzers/basic.py` — 수치형 분포(평균/중앙/표준편차/분위), 이상치(IQR)
- [x] `analyzers/basic.py` — 상관관계 계산
- [x] `report/text.py` — 분석 결과를 보기 좋은 텍스트로 출력
- [x] `cli.py` — `goldfish <csv경로>` 실행 → 텍스트 리포트
  - ⚠️ 메모: `종목코드`가 CSV에서 int64로 읽혀 수치 통계/상관에 포함됨(식별자라 통계 무의미, 앞자리 0 손실). v0.2 금융 스키마 검증에서 식별자 컬럼 제외 처리 예정.

### 마무리
- [x] `tests/test_basic.py` — basic analyzer 핵심 동작 테스트 (7개 통과)
- [x] `README.md` 초안 (소개/설치/사용 예시/면책 문구)
- [x] `LICENSE` 추가 (MIT)
- [x] **git init + 첫 커밋** (`.env` 안 올라갔는지 확인!) — `.env` 미포함·`.claude/` 제외 확인 후 커밋 `6b95b80`
- [x] **v0.1 동작 확인**: `goldfish examples/sample.csv` 결과 검증 — `pip install -e .` 후 CLI·pytest 통과

---

## 🟡 v0.2 — 금융 특화 진단 + 차트 (토스 ❌ / AI ❌)
> 목표: 범용 통계를 넘어 "금융 데이터만의 진단"과 시각화

### 금융 분석
- [ ] `analyzers/finance.py` — 포트폴리오 집중도/분산 (종목별 비중, 상위 N 편중도)
- [ ] `analyzers/finance.py` — 매매 패턴 (매수/매도 빈도, 거래 시간대 분포, 과매매 지표)
- [ ] `analyzers/finance.py` — 손절·익절 습관 (실현손익 분포)
- [ ] `analyzers/finance.py` — 수익률·변동성 통계 (기간 수익률, 표준편차)
- [ ] 금융 데이터 컬럼 스키마 정의/검증 (필수 컬럼 안내)

### 차트
- [ ] `report/charts.py` — 종목별 비중 차트 (파이/바)
- [ ] `report/charts.py` — 시간대별 거래 분포 차트
- [ ] `report/charts.py` — 수익률 분포 히스토그램
- [ ] 차트 이미지 파일 저장 기능

### 마무리
- [ ] `tests/test_finance.py` 추가
- [ ] README에 금융 분석 예시·차트 스크린샷 추가
- [ ] **v0.2 동작 확인**

> 🛑 **STOP — 루프 정지선**: 위 v0.2 항목이 모두 `[x]`가 되면 여기서 멈추고 사용자에게 보고한다.
> 사용자 확인 없이는 아래 v0.3 이후로 자동 진행하지 않는다. (다시 진행하려면 이 줄을 지우고 `/loop` 재실행)

---

## 🟠 v0.3 — AI 자연어 진단·코칭 (토스 ❌ / AI ✅)
> 목표: 분석 결과를 LLM이 사람 말로 해설·경고

- [ ] `google-genai` 의존성 추가(optional), `.env`에 `GEMINI_API_KEY` 양식 추가
- [ ] `ai/summarize.py` — 분석 결과(dict) → 프롬프트 구성
- [ ] `ai/summarize.py` — Gemini API(무료 티어) 호출 → 자연어 요약 반환
- [ ] 프롬프트 설계: "진단·설명만, 투자 추천 금지" 가드레일 명시
- [ ] AI 없이도 동작하도록 fallback 처리 (키 없으면 통계만 출력) — **기본값 = AI 끔**
- [ ] `cli.py`에 `--ai` 옵션 추가
- [ ] `report.summary` 로 자연어 요약 추출 API
- [ ] `tests/` — AI 모듈 mock 테스트
- [ ] README에 AI 요약 예시 추가
- [ ] **v0.3 동작 확인**

---

## 🔵 v0.4 — 토스 조회 로더 + HTML 리포트 (토스 ✅ / AI ✅)
> 목표: 실데이터 연동 + 완성형 리포트. **read-only 엄수**

### 토스 연동 (조회만)
- [ ] 토스증권 OpenAPI 문서 확인 → 조회 가능한 데이터/엔드포인트 정리
- [ ] 토스 API 이용약관 확인 (재배포/상표/파생물 조항)
- [ ] `loaders/toss.py` — 인증 (`.env` 키 사용, 절대 하드코딩 금지)
- [ ] `loaders/toss.py` — 포트폴리오/체결내역 조회 → DataFrame 변환
- [ ] ⚠️ 주문/매매 관련 엔드포인트는 **구현하지 않음** (read-only 가드)
- [ ] 토스 응답 → goldfish 표준 스키마 매핑

### HTML 리포트
- [ ] `report/html.py` — 차트 + 텍스트 + AI 요약을 HTML 한 장으로
- [ ] HTML 템플릿 디자인 (금붕어 브랜딩)
- [ ] `report.to_html(path)` API

### 마무리
- [ ] 토스 로더 테스트 (샌드박스/mock)
- [ ] README에 토스 연동 가이드 + 보안 경고
- [ ] **v0.4 동작 확인**

---

## 🟣 v1.0 — 배포 + 브랜딩
> 목표: `pip install goldfish` 로 누구나 사용

- [ ] PyPI에 `goldfish` 이름 사용 가능 여부 확인 (불가 시 대체명)
- [ ] 패키지 메타데이터 정리 (분류자/키워드/링크)
- [ ] 금붕어 🐠 마스코트/로고 제작
- [ ] README 완성 (배지, GIF 데모, 태그라인)
- [ ] `CONTRIBUTING.md` + 이슈/PR 템플릿
- [ ] GitHub Actions CI (테스트 자동 실행)
- [ ] TestPyPI 업로드 테스트
- [ ] **PyPI 정식 배포**
- [ ] GitHub 릴리스 v1.0 태그

---

## 📌 상시 원칙 (매 작업 시 점검)
1. 토스 API는 **조회만** — 주문/매매 코드 절대 금지
2. 키는 `.env`에만 — 커밋 전 항상 `git status`로 `.env` 미포함 확인
3. "추천" 아니라 "진단·설명" — 투자자문 아님 (면책 문구 유지)
4. `analyzers`는 AI/토스 없이도 동작해야 함
