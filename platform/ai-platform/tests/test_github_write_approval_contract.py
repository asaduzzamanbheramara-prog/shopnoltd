"""Static contract tests for the GitHub write approval security boundary.

These tests intentionally use only the Python standard library so they can run
without booting PostgreSQL, Keycloak, or external GitHub services.
"""
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "app" / "api" / "connections.py"
MODEL_PATH = ROOT / "app" / "db" / "models.py"


def _source(path):
    return path.read_text(encoding="utf-8")


def _tree(path):
    return ast.parse(_source(path), filename=str(path))


def _function(tree, name):
    return next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


class GitHubWriteApprovalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_source = _source(API_PATH)
        cls.api_tree = _tree(API_PATH)
        cls.model_tree = _tree(MODEL_PATH)

    def test_write_requires_admin_and_approval_id(self):
        fn = _function(self.api_tree, "github_write_file")
        args = {arg.arg: arg for arg in fn.args.args}
        self.assertIn("approval_id", self.api_source)
        self.assertIn("Depends(require_admin)", ast.unparse(fn))
        self.assertNotIn("approved: bool", self.api_source)
        self.assertIn("body.approval_id", ast.unparse(fn))

    def test_approval_is_bound_to_user_connection_and_operation(self):
        fn = _function(self.api_tree, "approve_github_write")
        source = ast.unparse(fn)
        self.assertIn("Depends(require_admin)", source)
        self.assertIn("connection_id", source)
        self.assertIn("user.get", source)
        self.assertIn("str(", source)
        self.assertIn("_github_write_digest(body)", source)
        self.assertIn("timedelta(minutes=5)", self.api_source)

    def test_approval_is_atomically_consumed_once(self):
        fn = _function(self.api_tree, "github_write_file")
        source = ast.unparse(fn)
        self.assertIn("GitHubWriteApproval.consumed_at.is_(None)", source)
        self.assertIn("values(consumed_at=now)", source)
        self.assertIn("db.commit()", source)
        self.assertIn("status.HTTP_409_CONFLICT", source)

    def test_digest_excludes_only_the_approval_identifier(self):
        fn = _function(self.api_tree, "_github_write_digest")
        source = ast.unparse(fn)
        self.assertIn('exclude={"approval_id"}', source)
        self.assertIn("sort_keys=True", source)
        self.assertIn("hashlib.sha256", source)

    def test_persistent_approval_model_has_expiry_and_consumption_fields(self):
        model = next(
            node for node in self.model_tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "GitHubWriteApproval"
        )
        fields = {
            target.id
            for node in model.body if isinstance(node, ast.AnnAssign)
            for target in [node.target] if isinstance(target, ast.Name)
        }
        self.assertTrue({
            "connection_id", "user_id", "operation_hash",
            "expires_at", "consumed_at",
        }.issubset(fields))


if __name__ == "__main__":
    unittest.main()
