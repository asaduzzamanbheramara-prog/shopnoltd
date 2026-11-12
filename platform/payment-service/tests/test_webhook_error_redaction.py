import ast
from pathlib import Path


def test_webhook_exception_responses_never_reflect_provider_errors():
    source = Path("app/api/webhooks.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    checked = 0
    for handler in (node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)):
        for node in ast.walk(handler):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "HTTPException":
                continue

            detail = node.args[1] if len(node.args) > 1 else None
            if detail is None:
                detail = next(
                    (kw.value for kw in node.keywords if kw.arg == "detail"),
                    None,
                )
            assert isinstance(detail, ast.Constant) and isinstance(detail.value, str), (
                "Webhook exception handlers must return fixed public messages, "
                "not interpolate provider exception or response details."
            )
            checked += 1

    assert checked >= 2, "Expected signature and provider-status error paths to be checked"
