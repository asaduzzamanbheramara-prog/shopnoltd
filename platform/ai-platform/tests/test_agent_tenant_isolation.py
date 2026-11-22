import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "app" / "api" / "agents.py"
MODELS_SOURCE = ROOT / "app" / "db" / "models.py"


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
        cls.model_tree = ast.parse(MODELS_SOURCE.read_text(encoding="utf-8"))
        cls.functions = {
            node.name: node
            for node in cls.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        cls.model_classes = {
            node.name: node
            for node in cls.model_tree.body
            if isinstance(node, ast.ClassDef)
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
        self.assertTrue(any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "strip"
            for node in ast.walk(helper)
        ))

    def test_tenant_context_runtime_behavior(self):
        helper_node = self.functions["current_tenant_id"]

        class FakeHTTPException(Exception):
            def __init__(self, status_code, detail):
                self.status_code = status_code
                self.detail = detail

        namespace = {"HTTPException": FakeHTTPException}
        module = ast.Module(body=[helper_node], type_ignores=[])
        exec(compile(module, str(SOURCE), "exec"), namespace)
        resolve_tenant = namespace["current_tenant_id"]

        self.assertEqual(resolve_tenant({"tenant_id": "tenant-a"}), "tenant-a")
        self.assertEqual(resolve_tenant({"tenant_id": "  tenant-a  "}), "tenant-a")
        for claims in ({}, {"tenant_id": None}, {"tenant_id": ""}, {"tenant_id": "   "}, {"tenant_id": 42}):
            with self.subTest(claims=claims):
                with self.assertRaises(FakeHTTPException) as raised:
                    resolve_tenant(claims)
                self.assertEqual(raised.exception.status_code, 403)

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

    def test_agent_api_uses_shared_database_session_and_metadata(self):
        imports = [
            node for node in self.tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        import_text = "\n".join(ast.unparse(node) for node in imports)
        self.assertIn("from app.db.models import Agent, Conversation", import_text)
        self.assertIn("from app.db.session import get_db", import_text)
        self.assertNotIn("app.core.db", import_text)
        self.assertNotIn("SessionLocal", import_text)
        for endpoint in ("create", "list_", "chat"):
            self.assertTrue(any(
                isinstance(default, ast.Call)
                and isinstance(default.func, ast.Name)
                and default.func.id == "Depends"
                and default.args
                and isinstance(default.args[0], ast.Name)
                and default.args[0].id == "get_db"
                for default in self.functions[endpoint].args.defaults
                + self.functions[endpoint].args.kw_defaults
                if default is not None
            ), endpoint)

    def test_agent_tables_are_registered_on_shared_base(self):
        for name, table in (("Agent", "agents"), ("Conversation", "ai_conversations")):
            node = self.model_classes[name]
            self.assertTrue(any(
                isinstance(base, ast.Name) and base.id == "Base"
                for base in node.bases
            ), name)
            self.assertTrue(any(
                isinstance(child, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "__tablename__" for target in child.targets)
                and isinstance(child.value, ast.Constant)
                and child.value.value == table
                for child in node.body
            ), name)

        conversation = self.model_classes["Conversation"]
        foreign_keys = [
            child for child in ast.walk(conversation)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "ForeignKey"
            and child.args
            and isinstance(child.args[0], ast.Constant)
        ]
        self.assertTrue(any(item.args[0].value == "agents.id" for item in foreign_keys))


if __name__ == "__main__":
    unittest.main()
