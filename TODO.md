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
- [x] `analyzers/finance.py` — 포트폴리오 집중도/분산 (종목별 비중, 상위 N 편중도) — 거래금액 기준 비중·HHI·상위N
- [x] `analyzers/finance.py` — 매매 패턴 (매수/매도 빈도, 거래 시간대 분포, 과매매 지표)
  - ⚠️ 메모: 샘플 데이터에 체결 '시각'이 없어 시간대 분포는 요일 분포로 대체(시각 있으면 자동 시각대 집계). 거래일당 체결 수를 과매매 지표로 사용.
- [x] `analyzers/finance.py` — 손절·익절 습관 (실현손익 분포) — 승률·손익비·평균 익절/손절
- [x] `analyzers/finance.py` — 수익률·변동성 통계 (기간 수익률, 표준편차)
  - ⚠️ 메모: 보유 평가액 시계열이 없어 실현손익 기반 추정(원가=거래금액-실현손익). 기간 수익률은 v0.4 토스 연동 후 정밀화 예정.
- [x] 금융 데이터 컬럼 스키마 정의/검증 (필수 컬럼 안내) — `validate_schema`/`is_finance_df`, 식별자(종목코드) 분리

### 차트
- [x] `report/charts.py` — 종목별 비중 차트 (가로 막대)
- [x] `report/charts.py` — 시간대별 거래 분포 차트 (요일/시각대 막대)
- [x] `report/charts.py` — 수익률 분포 히스토그램 (실현손익)
- [x] 차트 이미지 파일 저장 기능 — `save_all(df, outdir)` + CLI `--charts DIR`
  - ⚠️ 메모: matplotlib 는 선택 의존성(`goldfish[charts]`). 한글 폰트 자동 선택(Malgun Gothic 등), Agg 백엔드.

### 마무리
- [x] `tests/test_finance.py` 추가 (9개) · `tests/test_charts.py` 추가 (4개) — 총 20개 통과
- [x] README에 금융 분석 예시·차트 스크린샷 추가 (`docs/images/*.png`)
- [x] **v0.2 동작 확인** — `goldfish examples/sample.csv [--charts DIR]` 텍스트 진단 + PNG 3종 생성 확인

---

## 🟠 v0.3 — AI 자연어 진단·코칭 (토스 ❌ / AI ✅)
> 목표: 분석 결과를 LLM이 사람 말로 해설·경고

- [x] `google-genai` 의존성 추가(optional), `.env`에 `GEMINI_API_KEY` 양식 추가 — `[ai]` extra(`google-genai`, `python-dotenv`)·`.env.example`
- [x] `ai/summarize.py` — 분석 결과(dict) → 프롬프트 구성 — `build_prompt(basic, finance)`
- [x] `ai/summarize.py` — Gemini API(무료 티어) 호출 → 자연어 요약 반환 — `summarize()`, 호출부 `_call_gemini` 격리
- [x] 프롬프트 설계: "진단·설명만, 투자 추천 금지" 가드레일 명시 — `SYSTEM_GUARDRAIL`
- [x] AI 없이도 동작하도록 fallback 처리 (키 없으면 통계만 출력) — **기본값 = AI 끔** — `available()`/`unavailable_reason()`
- [x] `cli.py`에 `--ai` 옵션 추가 — 키 없으면 노란 안내 후 통계만(exit 0)
- [x] `report.summary` 로 자연어 요약 추출 API — `report/summary.py: summary(df)` → str|None
- [x] `tests/` — AI 모듈 mock 테스트 — `tests/test_ai.py` 8개 (총 28개 통과)
- [x] README에 AI 요약 예시 추가 — "AI 자연어 코칭 (v0.3)" 절
- [x] **v0.3 동작 확인** — `goldfish examples/sample.csv --ai` (키 없는 fallback) 검증 완료

---

## 🔵 v0.4 — 토스 조회 로더 + HTML 리포트 (토스 ✅ / AI ✅)
> 목표: 실데이터 연동 + 완성형 리포트. **read-only 엄수**

### 토스 연동 (조회만)
- [x] 토스증권 OpenAPI 문서 확인 → 조회 가능한 데이터/엔드포인트 정리 — base `openapi.tossinvest.com`, OAuth2 Client Credentials, GET accounts/holdings/orders
- [x] 토스 API 이용약관 확인 (재배포/상표/파생물 조항) — 검토 완료(2026-05-18 시행): 제5조③ 시세 본인 매매목적 한정·제3자 배포/상업적 활용 금지, 제5조④ 법인 제외, 제5조② 키 누설 금지. 별도 상표/파생물 조항 없음. README 준수 가이드 반영
- [x] `loaders/toss.py` — 인증 (`.env` 키 사용, 절대 하드코딩 금지) — `TossClient._access_token()`, `TOSS_CLIENT_ID/SECRET`
- [x] `loaders/toss.py` — 포트폴리오/체결내역 조회 → DataFrame 변환 — `get_accounts/get_holdings/get_orders`, `trades_dataframe()`
- [x] ⚠️ 주문/매매 관련 엔드포인트는 **구현하지 않음** (read-only 가드) — 인증 외 전부 GET, 주문 변경 메서드 부재(테스트로 강제)
- [x] 토스 응답 → goldfish 표준 스키마 매핑 — `orders_to_dataframe()` (체결완료 주문 → 체결일/종목코드/종목명/매매구분/수량/단가/거래금액)

### HTML 리포트
- [x] `report/html.py` — 차트 + 텍스트 + AI 요약을 HTML 한 장으로 — 차트 base64 인라인 임베드(자기완결), `--html` CLI 옵션
- [x] HTML 템플릿 디자인 (금붕어 브랜딩) — 골드(#f5a623) 팔레트·카드 레이아웃·집중도 막대·면책 푸터
- [x] `report.to_html(path)` API — `goldfish.report.to_html(df, path, ...)` / `render_html(df) -> str`

### 마무리
- [x] 토스 로더 테스트 (샌드박스/mock) — `tests/test_toss.py` 14개 (총 50개 통과)
- [x] README에 토스 연동 가이드 + 보안 경고 — 토스 연동·HTML 리포트 절 추가, read-only/키 보안/약관 경고
- [x] **v0.4 동작 확인** — `--html` 로 HTML 리포트 생성 검증(차트 3종 인라인 임베드), 전체 50개 테스트 통과

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

> 🛑 **STOP — 루프 정지선**: 위 v1.0 항목이 모두 `[x]`가 되면 여기서 멈추고 사용자에게 보고한다.
> v1.0 진행은 승인됨(정지선을 v1.0 끝으로 이동). 단, **되돌릴 수 없는 외부 공개 단계
> — TestPyPI/PyPI 정식 배포, GitHub 릴리스 태그 — 는 실행 직전 사용자 확인을 받는다**
> (자율 루프가 임의로 퍼블리시하지 않음. 자격증명도 필요). 그 외 준비 작업(이름 확인,
> 메타데이터, CI, 문서, 로고)은 자동 진행 가능.

---

## 📌 상시 원칙 (매 작업 시 점검)
1. 토스 API는 **조회만** — 주문/매매 코드 절대 금지
2. 키는 `.env`에만 — 커밋 전 항상 `git status`로 `.env` 미포함 확인
3. "추천" 아니라 "진단·설명" — 투자자문 아님 (면책 문구 유지)
4. `analyzers`는 AI/토스 없이도 동작해야 함
