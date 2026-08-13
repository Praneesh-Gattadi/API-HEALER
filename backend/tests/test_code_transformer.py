import os
import tempfile
import pytest

from app.models.migration_plan import MigrationPlan, MigrationAction, MigrationActionType
from app.services.code_transformer import apply_transform

@pytest.fixture
def plan_rename():
    return MigrationPlan(
        summary="Test plan",
        risk_level="LOW",
        actions=[
            MigrationAction(
                action_type=MigrationActionType.rename_field,
                description="Rename user_id to id",
                old_name="user_id",
                new_name="id",
                affected_path="/test",
                rationale="test",
                validation_required="none"
            )
        ]
    )

@pytest.fixture
def plan_remove():
    return MigrationPlan(
        summary="Test plan",
        risk_level="LOW",
        actions=[
            MigrationAction(
                action_type=MigrationActionType.remove_field,
                description="Remove user_id",
                old_name="user_id",
                affected_path="/test",
                rationale="test",
                validation_required="none"
            )
        ]
    )

def test_unsupported_remove_field(plan_remove):
    with tempfile.TemporaryDirectory() as tmpdir:
        res = apply_transform(plan_remove, tmpdir, dry_run=False)
        assert len(res.warnings) == 1
        assert "unsupported_transformation: remove_field" in res.warnings[0].message
        assert len(res.changes) == 0

def test_path_traversal_rejected(plan_rename):
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = os.path.join(tmpdir, "..", "outside.py")
        # create a dummy file to try and traverse to if possible, but actually apply_transform walks the repo_root.
        # to test traversal, we can't easily force os.walk to go out, but we can verify our `is_safe_path` check.
        from app.services.code_transformer import is_safe_path
        assert not is_safe_path(tmpdir, os.path.join(tmpdir, "..", "outside.py"))
        assert not is_safe_path(tmpdir, os.path.join(tmpdir, ".git", "config.py"))

def test_rename_pydantic_model_field_positive(plan_rename):
    code = "from pydantic import BaseModel\nclass User(BaseModel):\n    user_id: str"
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "models.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert res.success
        assert len(res.changes) == 1
        assert "id: str" in res.changes[0].diff
        
        with open(file_path, "r") as f:
            assert "    id: str" in f.read()

def test_rename_keyword_arg_positive(plan_rename):
    code = "user = User(user_id=1)"
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert res.success
        assert len(res.changes) == 1
        assert "id=1" in res.changes[0].diff
        
        with open(file_path, "r") as f:
            assert "User(id=1)" in f.read()

def test_dry_run_does_not_modify_file(plan_rename):
    code = "user = User(user_id=1)"
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=True)
        assert res.success
        assert len(res.changes) == 1
        
        with open(file_path, "r") as f:
            assert "User(user_id=1)" in f.read() # unchanged

def test_unrelated_dictionary_negative(plan_rename):
    code = 'data = {"user_id": 1}'
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert len(res.changes) == 0
        assert any("review_required: skipped dict key 'user_id'" in w.message for w in res.warnings)

def test_unrelated_variable_negative(plan_rename):
    code = 'user_id = 1'
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert len(res.changes) == 0
        assert any("review_required: skipped variable assignment 'user_id'" in w.message for w in res.warnings)

def test_similarly_named_variable_negative(plan_rename):
    code = 'database_user_id = 1'
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert len(res.changes) == 0
        assert len(res.warnings) == 0

def test_unrelated_method_negative(plan_rename):
    code = 'def get_user_id():\n    pass\nget_user_id()'
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert len(res.changes) == 0
        assert len(res.warnings) == 0

def test_unrelated_class_negative(plan_rename):
    code = 'class DatabaseUser:\n    user_id: str'
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert len(res.changes) == 0
        assert any("review_required: skipped field 'user_id'" in w.message for w in res.warnings)

def test_comments_and_docstrings_negative(plan_rename):
    code = 'def x():\n    """This uses user_id"""\n    # also user_id\n    pass'
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        res = apply_transform(plan_rename, tmpdir, dry_run=False)
        assert len(res.changes) == 0
        assert len(res.warnings) == 0

def test_rollback_on_syntax_error(plan_rename):
    # This test manually breaks the syntax check to ensure rollback triggers
    code = "class User(BaseModel):\n    user_id: str"
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "models.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        import app.services.code_transformer as ct
        original_ast_parse = ct.ast.parse
        
        def mock_parse(*args, **kwargs):
            raise SyntaxError("Mocked syntax error")
            
        ct.ast.parse = mock_parse
        try:
            res = apply_transform(plan_rename, tmpdir, dry_run=False)
            assert not res.success
            assert any("Syntax error" in err for err in res.errors)
            assert len(res.changes) == 0
            
            with open(file_path, "r") as f:
                assert "user_id: str" in f.read() # reverted
        finally:
            ct.ast.parse = original_ast_parse
