"""토스 조회 로더 테스트 — 실제 네트워크/requests 없이 mock 으로 검증.

``requests`` 가 설치돼 있지 않은 환경에서도 통과해야 한다(선택 의존성).
실제 HTTP(``_http``)와 가용성 판단(``unavailable_reason``)만 monkeypatch 하고,
나머지 로직(토큰 캐시·페이징·스키마 매핑·fallback)은 진짜로 실행한다.
"""
from __future__ import annotations

import importlib

import pandas as pd

from goldfish.analyzers.finance import REQUIRED_COLUMNS, is_finance_df

toss = importlib.import_module("goldfish.loaders.toss")


# --- 가짜 HTTP 라우터 --------------------------------------------------------

def _fake_router(routes):
    """경로별 응답을 돌려주는 ``_http`` 대체 함수를 만든다.

    routes: {(METHOD, path_suffix): payload_or_callable}
    """
    calls: list[tuple[str, str, dict]] = []

    def fake_http(method, url, *, headers=None, params=None, data=None, timeout=15.0):
        calls.append((method, url, params or {}))
        for (m, suffix), payload in routes.items():
            if m == method and url.endswith(suffix):
                return payload(params) if callable(payload) else payload
        raise AssertionError(f"라우트 미정의: {method} {url}")

    fake_http.calls = calls
    return fake_http


_TOKEN = {"access_token": "tok-123", "token_type": "Bearer", "expires_in": 3600}


def _order(symbol, side, qty, price, amount, filled_at):
    return {
        "orderId": f"{symbol}-{side}-{filled_at}",
        "symbol": symbol,
        "side": side,
        "status": "FILLED",
        "execution": {
            "filledQuantity": qty,
            "averageFilledPrice": price,
            "filledAmount": amount,
            "filledAt": filled_at,
        },
    }


# --- 가용성 / fallback ------------------------------------------------------

def _force_no_creds(monkeypatch):
    monkeypatch.delenv(toss.ENV_CLIENT_ID, raising=False)
    monkeypatch.delenv(toss.ENV_CLIENT_SECRET, raising=False)
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)


def test_unavailable_when_no_credentials(monkeypatch):
    _force_no_creds(monkeypatch)
    reason = toss.unavailable_reason()
    assert reason is not None
    assert toss.ENV_CLIENT_ID in reason
    assert toss.available() is False


def test_load_toss_trades_raises_when_unavailable(monkeypatch):
    _force_no_creds(monkeypatch)
    try:
        toss.load_toss_trades()
    except toss.TossUnavailable:
        pass
    else:  # pragma: no cover
        raise AssertionError("자격증명 없을 때 TossUnavailable 가 발생해야 한다")


# --- 스키마 매핑 ------------------------------------------------------------

def test_orders_to_dataframe_maps_standard_schema():
    orders = [
        _order("005930", "BUY", 6, 70660.0, 423960.0, "2025-06-03T10:00:00+09:00"),
        _order("068270", "SELL", 12, 185750.0, 2229000.0, "2025-06-03T11:30:00+09:00"),
    ]
    df = toss.orders_to_dataframe(orders)
    assert list(df.columns) == ["체결일", "종목코드", "종목명", "매매구분", "수량", "단가", "거래금액"]
    assert df.loc[0, "체결일"] == "2025-06-03"
    assert df.loc[0, "종목코드"] == "005930"
    assert df.loc[0, "매매구분"] == "매수"
    assert df.loc[1, "매매구분"] == "매도"
    assert df.loc[1, "수량"] == 12
    # finance 분석기가 받아들이는 표준 스키마인지(필수 컬럼 충족)
    assert set(REQUIRED_COLUMNS).issubset(df.columns)
    assert is_finance_df(df)


def test_orders_to_dataframe_skips_unfilled():
    orders = [
        _order("005930", "BUY", 6, 70660.0, 423960.0, "2025-06-03T10:00:00+09:00"),
        {  # 취소되어 체결 수량 0 — 거래내역에서 제외돼야 함
            "orderId": "x",
            "symbol": "000660",
            "side": "BUY",
            "status": "CANCELED",
            "execution": {"filledQuantity": 0, "averageFilledPrice": 0,
                          "filledAmount": 0, "filledAt": None},
        },
    ]
    df = toss.orders_to_dataframe(orders)
    assert len(df) == 1
    assert df.loc[0, "종목코드"] == "005930"


def test_orders_to_dataframe_empty():
    df = toss.orders_to_dataframe([])
    assert df.empty
    assert list(df.columns) == ["체결일", "종목코드", "종목명", "매매구분", "수량", "단가", "거래금액"]


# --- 토큰 / 조회 / 페이징 ---------------------------------------------------

def test_token_is_cached(monkeypatch):
    fake = _fake_router({("POST", "/oauth2/token"): _TOKEN,
                         ("GET", "/api/v1/accounts"): {"result": [{"accountSeq": 7}]}})
    monkeypatch.setattr(toss, "_http", fake)
    client = toss.TossClient("cid", "secret")
    assert client.get_accounts()[0]["accountSeq"] == 7
    client.get_accounts()
    # 토큰 발급은 캐시되어 단 한 번만 호출돼야 한다
    token_calls = [c for c in fake.calls if c[0] == "POST"]
    assert len(token_calls) == 1


def test_get_orders_follows_cursor(monkeypatch):
    page1 = {"result": {"orders": [
        _order("005930", "BUY", 1, 100.0, 100.0, "2025-06-01T10:00:00+09:00")],
        "nextCursor": "c2", "hasNext": True}}
    page2 = {"result": {"orders": [
        _order("005930", "SELL", 1, 110.0, 110.0, "2025-06-02T10:00:00+09:00")],
        "nextCursor": None, "hasNext": False}}
    state = {"n": 0}

    def orders_route(params):
        state["n"] += 1
        return page1 if state["n"] == 1 else page2

    fake = _fake_router({
        ("POST", "/oauth2/token"): _TOKEN,
        ("GET", "/api/v1/orders"): orders_route,
    })
    monkeypatch.setattr(toss, "_http", fake)
    client = toss.TossClient("cid", "secret", account_seq=7)
    orders = client.get_orders(status="CLOSED")
    assert len(orders) == 2
    assert state["n"] == 2  # 두 페이지를 모두 수집


def test_trades_dataframe_uses_first_account_when_unset(monkeypatch):
    orders_payload = {"result": {"orders": [
        _order("005930", "BUY", 6, 70660.0, 423960.0, "2025-06-03T10:00:00+09:00")],
        "nextCursor": None, "hasNext": False}}
    fake = _fake_router({
        ("POST", "/oauth2/token"): _TOKEN,
        ("GET", "/api/v1/accounts"): {"result": [{"accountSeq": 42}]},
        ("GET", "/api/v1/orders"): orders_payload,
    })
    monkeypatch.setattr(toss, "_http", fake)
    client = toss.TossClient("cid", "secret")  # account_seq 미지정
    df = client.trades_dataframe()
    assert len(df) == 1
    assert client.account_seq == 42  # 첫 계좌로 확정됐는지


def test_holdings_passes_account_header(monkeypatch):
    seen = {}

    def fake_http(method, url, *, headers=None, params=None, data=None, timeout=15.0):
        if url.endswith("/oauth2/token"):
            return _TOKEN
        seen["headers"] = headers
        return {"result": {"items": []}}

    monkeypatch.setattr(toss, "_http", fake_http)
    client = toss.TossClient("cid", "secret", account_seq=99)
    client.get_holdings()
    assert seen["headers"]["X-Tossinvest-Account"] == "99"
    assert seen["headers"]["Authorization"] == "Bearer tok-123"


# --- read-only 가드 ---------------------------------------------------------

def test_client_has_no_order_mutation_methods():
    """주문 생성/정정/취소 메서드가 존재하지 않아야 한다(read-only 보장)."""
    for forbidden in ("create_order", "modify_order", "cancel_order", "place_order"):
        assert not hasattr(toss.TossClient, forbidden)


def test_friendly_http_error_auth_and_rate_limit():
    assert "인증 실패" in toss._friendly_http_error(401, "")
    assert "한도 초과" in toss._friendly_http_error(429, "")
    assert "\n" not in toss._friendly_http_error(500, "boom\ndetail\nmore")
