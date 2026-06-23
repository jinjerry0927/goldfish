"""토스증권 Open API 조회(read-only) 로더 — 거래내역을 표준 스키마 DataFrame 으로.

설계 원칙
---------
* **read-only 엄수**: 시세·계좌·보유주식·주문 '조회' 만 한다. 주문 생성/정정/취소
  (``POST /api/v1/orders`` 계열)는 이 모듈에 **의도적으로 구현하지 않는다**.
  인증 외 모든 호출은 GET 으로 제한된다(:func:`_authed_get`).
* **선택 의존성**: HTTP 클라이언트 ``requests`` 는 ``pip install 'goldfish[toss]'``
  일 때만 필요. 미설치 상태에서도 이 모듈은 import 되어야 하므로 import 는
  호출 시점까지 미룬다.
* **기본 끔**: 키가 없으면 :class:`TossUnavailable` 로 알리고, 호출 측이 잡아
  안내 후 건너뛰도록 한다(AI 계층과 동일한 fallback 패턴).
* **키 하드코딩 금지**: 자격증명은 인자 > 환경변수(.env) 에서만 읽는다.
* **테스트 가능**: 실제 네트워크는 :func:`_http` 한 곳에 격리한다(테스트는 이 함수만
  monkeypatch).

표준 스키마 매핑 (``GET /api/v1/orders`` 의 종료·체결 주문 → 거래내역)
    체결일   ← execution.filledAt (날짜)
    종목코드 ← symbol
    종목명   ← symbol (주문 응답에 종목명이 없어 심볼로 대체)
    매매구분 ← side (BUY→매수, SELL→매도)
    수량     ← execution.filledQuantity
    단가     ← execution.averageFilledPrice
    거래금액 ← execution.filledAmount
    (실현손익은 주문 조회 API 에 없어 컬럼을 만들지 않는다 → finance 의 선택 컬럼)

⚠️ 진단·설명용 데이터 조회이며 투자 추천/주문 실행이 아니다.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import pandas as pd

BASE_URL = "https://openapi.tossinvest.com"

ENV_CLIENT_ID = "TOSS_CLIENT_ID"
ENV_CLIENT_SECRET = "TOSS_CLIENT_SECRET"
ENV_ACCOUNT_SEQ = "TOSS_ACCOUNT_SEQ"

# 주문 side → 표준 스키마 매매구분
_SIDE_KO = {"BUY": "매수", "SELL": "매도"}

# 표준 스키마 컬럼 순서(실현손익은 주문 API 에 없으므로 제외)
_TRADE_COLUMNS = ["체결일", "종목코드", "종목명", "매매구분", "수량", "단가", "거래금액"]


class TossUnavailable(RuntimeError):
    """토스 조회를 할 수 없는 상태(키 없음·라이브러리 미설치 등)."""


class TossAPIError(RuntimeError):
    """토스 API 가 에러 응답(비 2xx)을 돌려준 경우."""


# --- 자격증명 / 가용성 -------------------------------------------------------

def _resolve_credentials(
    client_id: Optional[str], client_secret: Optional[str]
) -> Optional[tuple[str, str]]:
    """명시 인자 > 환경변수 순으로 (client_id, client_secret) 을 찾는다.

    ``python-dotenv`` 가 있으면 ``.env`` 를 환경에 반영(없으면 무시). 둘 중 하나라도
    비어 있으면 ``None`` 을 반환한다.
    """
    if not (client_id and client_secret):
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass
    cid = (client_id or os.environ.get(ENV_CLIENT_ID, "")).strip()
    secret = (client_secret or os.environ.get(ENV_CLIENT_SECRET, "")).strip()
    if cid and secret:
        return cid, secret
    return None


def unavailable_reason(
    client_id: Optional[str] = None, client_secret: Optional[str] = None
) -> Optional[str]:
    """토스 조회를 쓸 수 없는 이유를 사람이 읽을 문자열로. 사용 가능하면 ``None``."""
    if _resolve_credentials(client_id, client_secret) is None:
        return (
            f"{ENV_CLIENT_ID}/{ENV_CLIENT_SECRET} 가 설정되지 않았습니다 "
            "(.env 또는 환경변수)."
        )
    try:
        import requests  # noqa: F401
    except ImportError:
        return "requests 미설치: pip install 'goldfish[toss]'"
    return None


def available(
    client_id: Optional[str] = None, client_secret: Optional[str] = None
) -> bool:
    """자격증명과 라이브러리가 모두 준비됐으면 ``True``."""
    return unavailable_reason(client_id, client_secret) is None


# --- 네트워크 격리 계층 ------------------------------------------------------

def _http(
    method: str,
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """실제 HTTP 호출 — 네트워크 의존부를 한 곳에 격리(테스트는 이 함수만 대체).

    ``requests`` 를 호출 시점에 import 한다(선택 의존성). 비 2xx 응답은
    :class:`TossAPIError` 로 변환한다.
    """
    import requests

    resp = requests.request(
        method, url, headers=headers, params=params, data=data, timeout=timeout
    )
    if not resp.ok:
        raise TossAPIError(_friendly_http_error(resp.status_code, resp.text))
    return resp.json()


def _friendly_http_error(status_code: int, body: str) -> str:
    """HTTP 에러를 사람이 읽을 짧은 한 줄 메시지로 변환한다."""
    if status_code in (401, 403):
        return f"인증 실패({status_code}) — {ENV_CLIENT_ID}/{ENV_CLIENT_SECRET} 값을 확인하세요."
    if status_code == 429:
        return "요청 한도 초과(429) — 잠시 후 다시 시도하세요(Retry-After 만큼 대기 권장)."
    snippet = " ".join((body or "").split())[:160]
    return f"토스 API 호출 실패({status_code}): {snippet}"


# --- 조회 전용 클라이언트 ----------------------------------------------------

class TossClient:
    """토스증권 Open API 조회 클라이언트(read-only).

    인증(토큰 발급) 외에는 GET 조회만 노출한다. 주문 실행 메서드는 없다.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        account_seq: Optional[int] = None,
        base_url: str = BASE_URL,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_seq = account_seq
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None

    # 인증 ------------------------------------------------------------------
    def _access_token(self) -> str:
        """Client Credentials Grant 로 access token 을 발급/캐시한다."""
        if self._token:
            return self._token
        payload = _http(
            "POST",
            f"{self.base_url}/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        token = (payload or {}).get("access_token")
        if not token:
            raise TossAPIError("토큰 응답에 access_token 이 없습니다.")
        self._token = token
        return token

    def _authed_get(
        self, path: str, *, params: Optional[dict[str, Any]] = None, account: bool = False
    ) -> Any:
        """토큰(+필요 시 계좌 헤더)으로 GET 조회. 조회 전용 헬퍼.

        envelope ``{"result": ...}`` 의 ``result`` 를 풀어 반환한다.
        """
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        if account:
            headers["X-Tossinvest-Account"] = str(self._require_account_seq())
        payload = _http("GET", f"{self.base_url}{path}", headers=headers, params=params)
        if isinstance(payload, dict) and "result" in payload:
            return payload["result"]
        return payload

    def _require_account_seq(self) -> int:
        """사용할 accountSeq 를 확정한다(미지정 시 첫 계좌)."""
        if self.account_seq is not None:
            return self.account_seq
        accounts = self.get_accounts()
        if not accounts:
            raise TossAPIError("조회된 계좌가 없습니다.")
        self.account_seq = int(accounts[0]["accountSeq"])
        return self.account_seq

    # 조회 ------------------------------------------------------------------
    def get_accounts(self) -> list[dict[str, Any]]:
        """계좌 목록 조회 (``GET /api/v1/accounts``)."""
        result = self._authed_get("/api/v1/accounts")
        return list(result or [])

    def get_holdings(self) -> dict[str, Any]:
        """보유 주식 조회 (``GET /api/v1/holdings``)."""
        return self._authed_get("/api/v1/holdings", account=True) or {}

    def get_orders(
        self,
        *,
        status: str = "CLOSED",
        symbol: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """주문 목록 조회 (``GET /api/v1/orders``). CLOSED 는 커서로 전 페이지 수집.

        Args:
            status: ``CLOSED``(종료) 또는 ``OPEN``(진행 중).
            symbol: 특정 종목만 필터(선택).
            date_from / date_to: 주문일 기준 범위(``YYYY-MM-DD``, KST, 선택).
            limit: CLOSED 페이지 크기(최대 100).
            max_pages: 무한 루프 방지용 페이지 상한.
        """
        base_params: dict[str, Any] = {"status": status}
        if symbol:
            base_params["symbol"] = symbol
        if date_from:
            base_params["from"] = date_from
        if date_to:
            base_params["to"] = date_to

        orders: list[dict[str, Any]] = []
        cursor: Optional[str] = None
        for _ in range(max_pages):
            params = dict(base_params)
            if status == "CLOSED":
                params["limit"] = limit
                if cursor:
                    params["cursor"] = cursor
            result = self._authed_get("/api/v1/orders", params=params, account=True) or {}
            orders.extend(result.get("orders") or [])
            if status != "CLOSED" or not result.get("hasNext"):
                break
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return orders

    def trades_dataframe(
        self,
        *,
        symbol: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> pd.DataFrame:
        """체결 완료된 종료 주문을 goldfish 표준 스키마 DataFrame 으로 변환한다."""
        orders = self.get_orders(
            status="CLOSED", symbol=symbol, date_from=date_from, date_to=date_to
        )
        return orders_to_dataframe(orders)


# --- 변환 / 편의 진입점 ------------------------------------------------------

def orders_to_dataframe(orders: list[dict[str, Any]]) -> pd.DataFrame:
    """토스 주문 목록(dict) → 표준 스키마 DataFrame. 체결 수량 0 인 주문은 제외."""
    rows: list[dict[str, Any]] = []
    for order in orders:
        execution = order.get("execution") or {}
        filled = _to_float(execution.get("filledQuantity"))
        if not filled:  # 미체결(취소/거부 등)은 거래내역에서 제외
            continue
        symbol = order.get("symbol")
        rows.append(
            {
                "체결일": _to_date(execution.get("filledAt")),
                "종목코드": symbol,
                "종목명": symbol,  # 주문 응답에 종목명이 없어 심볼로 대체
                "매매구분": _SIDE_KO.get(str(order.get("side", "")).upper(), order.get("side")),
                "수량": filled,
                "단가": _to_float(execution.get("averageFilledPrice")),
                "거래금액": _to_float(execution.get("filledAmount")),
            }
        )
    return pd.DataFrame(rows, columns=_TRADE_COLUMNS)


def load_toss_trades(
    *,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    account_seq: Optional[int] = None,
    symbol: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> pd.DataFrame:
    """환경변수/.env 의 자격증명으로 토스 체결내역을 표준 스키마 DataFrame 으로 로드.

    Raises:
        TossUnavailable: 자격증명이 없거나 ``requests`` 가 설치되지 않은 경우.
            (호출 측에서 잡아 안내 후 건너뛰는 fallback 을 구현한다.)
    """
    reason = unavailable_reason(client_id, client_secret)
    if reason is not None:
        raise TossUnavailable(reason)
    creds = _resolve_credentials(client_id, client_secret)
    assert creds is not None  # unavailable_reason 통과 → 자격증명 존재 보장
    cid, secret = creds

    if account_seq is None:
        env_seq = os.environ.get(ENV_ACCOUNT_SEQ, "").strip()
        account_seq = int(env_seq) if env_seq else None

    client = TossClient(cid, secret, account_seq=account_seq)
    return client.trades_dataframe(symbol=symbol, date_from=date_from, date_to=date_to)


# --- 작은 변환 헬퍼 ----------------------------------------------------------

def _to_float(value: Any) -> float:
    """BigDecimal(숫자/문자열) → float. 변환 불가 시 0.0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_date(value: Any) -> Any:
    """ISO 8601 일시 문자열 → ``YYYY-MM-DD`` 문자열. 실패 시 원본 유지."""
    if not value:
        return value
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return value
    return ts.strftime("%Y-%m-%d")
