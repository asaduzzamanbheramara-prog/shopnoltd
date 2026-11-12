import asyncio

from app.api import direct_payment_proxy


def test_direct_payment_verification_proxy_route_is_registered():
    route = next(
        route
        for route in direct_payment_proxy.router.routes
        if getattr(route, "path", None)
        == "/direct-payments/submissions/{submission_id}/verify"
    )
    assert "POST" in route.methods


def test_direct_payment_verification_proxy_forwards_submission_and_evidence(monkeypatch):
    calls = []

    async def fake_proxy(method, path, access_token, **kwargs):
        calls.append((method, path, access_token, kwargs))
        return {"status": "verified", "transaction_id": "tx-123"}

    monkeypatch.setattr(direct_payment_proxy, "proxy", fake_proxy)
    route = next(
        route
        for route in direct_payment_proxy.router.routes
        if getattr(route, "path", None)
        == "/direct-payments/submissions/{submission_id}/verify"
    )
    body = {
        "manual_review_reason": "Reviewed bank receipt and matched reference",
        "amount": 125.0,
        "receiver_number": "01700000000",
    }
    result = asyncio.run(
        route.endpoint(
            submission_id="submission-123",
            body=body,
            access_token="signed-access-token",
        )
    )

    assert result == {"status": "verified", "transaction_id": "tx-123"}
    assert calls == [
        (
            "POST",
            "/api/v1/direct-payments/submissions/submission-123/verify",
            "signed-access-token",
            {"json": body},
        )
    ]


def test_payment_proxy_redacts_upstream_server_error_details(monkeypatch):
    class Response:
        status_code = 502
        text = '{"detail":"provider secret token=do-not-leak"}'

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(direct_payment_proxy.httpx, "AsyncClient", Client)
    try:
        asyncio.run(
            direct_payment_proxy.proxy(
                "POST", "/api/v1/direct-payments/submissions/s1/verify",
                "access-token",
            )
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 502
        assert exc.detail == "Payment service is temporarily unavailable"
        assert "do-not-leak" not in str(exc)
    else:
        raise AssertionError("expected sanitized HTTPException")


def test_payment_proxy_does_not_forward_upstream_client_error_body(monkeypatch):
    from fastapi import HTTPException

    class Response:
        status_code = 422
        text = '{"detail":"internal validation path /srv/private"}'

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(direct_payment_proxy.httpx, "AsyncClient", Client)
    try:
        asyncio.run(
            direct_payment_proxy.proxy(
                "POST", "/api/v1/direct-payments/submissions/s1/verify",
                "access-token",
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "Payment request was rejected"
        assert "/srv/private" not in str(exc)
    else:
        raise AssertionError("expected sanitized HTTPException")
