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
