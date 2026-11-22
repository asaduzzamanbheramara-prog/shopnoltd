import ast
from pathlib import Path
import unittest


SOURCE = Path(__file__).parents[1] / "app" / "api" / "agents.py"


def calls_named(node, name):
    return [
        child for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == name
    ]


def has_attribute_comparison(node, attribute, value):
    return any(
        isinstance(child, ast.Compare)
        and isinstance(child.left, ast.Attribute)
        and child.left.attr == attribute
        and any(
            isinstance(comparator, ast.Name) and comparator.id == value
            for comparator in child.comparators
        )
        for child in ast.walk(node)
    )


class AgentTenantIsolationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls.functions = {
            node.name: node
            for node in cls.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_tenant_context_fails_closed(self):
        helper = self.functions["current_tenant_id"]
        tenant_lookup = [
            call for call in ast.walk(helper)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "user"
            and call.func.attr == "get"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == "tenant_id"
        ]
        self.assertEqual(len(tenant_lookup), 1)
        self.assertTrue(calls_named(helper, "isinstance"))
        self.assertTrue(calls_named(helper, "HTTPException"))
        self.assertTrue(any(
            isinstance(node, ast.Constant) and node.value == 403
            for node in ast.walk(helper)
        ))
        self.assertFalse(any(
            isinstance(node, ast.Constant) and node.value == "default"
            for node in ast.walk(helper)
        ))

    def test_agent_creation_and_listing_require_tenant_context(self):
        for endpoint in ("create", "list_"):
            node = self.functions[endpoint]
            tenant_calls = calls_named(node, "current_tenant_id")
            self.assertTrue(any(
                call.args and isinstance(call.args[0], ast.Name)
                and call.args[0].id == "user"
                for call in tenant_calls
            ), endpoint)

    def test_chat_query_scopes_agent_id_and_tenant(self):
        chat = self.functions["chat"]
        self.assertTrue(calls_named(chat, "current_tenant_id"))
        self.assertTrue(has_attribute_comparison(chat, "id", "agent_id"))
        self.assertTrue(has_attribute_comparison(chat, "tenant_id", "tenant_id"))
        self.assertTrue(calls_named(chat, "HTTPException"))
        self.assertTrue(any(
            isinstance(node, ast.Constant) and node.value == 404
            for node in ast.walk(chat)
        ))


if __name__ == "__main__":
    unittest.main()
