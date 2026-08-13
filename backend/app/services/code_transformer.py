import os
import ast
import hashlib
import difflib
import libcst as cst
from typing import List

from app.models.migration_plan import MigrationPlan, MigrationAction, MigrationActionType
from app.models.transformation_result import TransformationResult, FileChange, TransformWarning

class MigrationTransformer(cst.CSTTransformer):
    def __init__(self, plan: MigrationPlan, file_path: str):
        self.plan = plan
        self.file_path = file_path
        self.warnings: List[TransformWarning] = []
        
        self.in_pydantic_model = False
        self.in_model_call = False
        self.in_annotated_assignment = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base.value, cst.Name) and base.value.value == "BaseModel":
                self.in_pydantic_model = True
                break
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        self.in_pydantic_model = False
        return updated_node

    def visit_Call(self, node: cst.Call) -> bool:
        if isinstance(node.func, cst.Name) and node.func.value[0].isupper():
            self.in_model_call = True
        return True

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        self.in_model_call = False
        return updated_node

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        if isinstance(node.annotation.annotation, cst.Name) and node.annotation.annotation.value[0].isupper():
            self.in_annotated_assignment = True
        return True

    def leave_AnnAssign(self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign) -> cst.AnnAssign:
        for action in self.plan.actions:
            if action.action_type == MigrationActionType.rename_field and action.old_name:
                if isinstance(original_node.target, cst.Name) and original_node.target.value == action.old_name:
                    if self.in_pydantic_model:
                        updated_node = updated_node.with_changes(target=cst.Name(action.new_name))
                    else:
                        self.warnings.append(TransformWarning(
                            file_path=self.file_path,
                            message=f"review_required: skipped field '{action.old_name}' (not in a Pydantic model)"
                        ))
        self.in_annotated_assignment = False
        return updated_node

    def leave_Arg(self, original_node: cst.Arg, updated_node: cst.Arg) -> cst.Arg:
        if original_node.keyword and isinstance(original_node.keyword, cst.Name):
            for action in self.plan.actions:
                if action.action_type == MigrationActionType.rename_field and action.old_name:
                    if original_node.keyword.value == action.old_name:
                        if self.in_model_call:
                            updated_node = updated_node.with_changes(keyword=cst.Name(action.new_name))
                        else:
                            self.warnings.append(TransformWarning(
                                file_path=self.file_path,
                                message=f"review_required: skipped keyword arg '{action.old_name}' (insufficient context)"
                            ))
        return updated_node

    def leave_DictElement(self, original_node: cst.DictElement, updated_node: cst.DictElement) -> cst.DictElement:
        if isinstance(original_node.key, cst.SimpleString):
            key_value = original_node.key.value.strip('"\'')
            for action in self.plan.actions:
                if action.action_type == MigrationActionType.rename_field and action.old_name:
                    if key_value == action.old_name:
                        if self.in_annotated_assignment:
                            new_key = original_node.key.value.replace(action.old_name, action.new_name)
                            updated_node = updated_node.with_changes(key=cst.SimpleString(new_key))
                        else:
                            self.warnings.append(TransformWarning(
                                file_path=self.file_path,
                                message=f"review_required: skipped dict key '{action.old_name}' (insufficient context)"
                            ))
        return updated_node

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        for target in original_node.targets:
            if isinstance(target.target, cst.Name):
                for action in self.plan.actions:
                    if action.action_type == MigrationActionType.rename_field and action.old_name:
                        if target.target.value == action.old_name:
                            self.warnings.append(TransformWarning(
                                file_path=self.file_path,
                                message=f"review_required: skipped variable assignment '{action.old_name}'"
                            ))
        return updated_node

def is_safe_path(repo_root: str, file_path: str) -> bool:
    abs_repo = os.path.abspath(repo_root)
    abs_file = os.path.abspath(file_path)
    if not abs_file.startswith(abs_repo):
        return False
    
    parts = abs_file.split(os.sep)
    excluded = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
    for part in parts:
        if part in excluded:
            return False
    return True

def apply_transform(plan: MigrationPlan, repo_root: str, dry_run: bool = True) -> TransformationResult:
    result = TransformationResult(success=True)
    
    # Process unsupported actions first
    for action in plan.actions:
        if action.action_type == MigrationActionType.remove_field:
            result.warnings.append(TransformWarning(
                message=f"unsupported_transformation: remove_field for '{action.old_name}' is not supported automatically. Review required."
            ))
        elif action.action_type not in (MigrationActionType.rename_field,):
            result.warnings.append(TransformWarning(
                message=f"unsupported_transformation: {action.action_type.value} is not supported."
            ))

    if not os.path.isdir(repo_root):
        result.success = False
        result.errors.append(f"Repository root does not exist: {repo_root}")
        return result

    for root, _, files in os.walk(repo_root):
        for file in files:
            if not file.endswith(".py"):
                continue
            
            file_path = os.path.join(root, file)
            if not is_safe_path(repo_root, file_path):
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            try:
                tree = cst.parse_module(original_content)
            except Exception as e:
                result.errors.append(f"Failed to parse {file_path}: {e}")
                continue

            transformer = MigrationTransformer(plan, file_path)
            new_tree = tree.visit(transformer)
            
            result.warnings.extend(transformer.warnings)
            
            proposed_content = new_tree.code
            if proposed_content != original_content:
                orig_hash = hashlib.sha256(original_content.encode()).hexdigest()
                prop_hash = hashlib.sha256(proposed_content.encode()).hexdigest()
                
                diff_lines = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    proposed_content.splitlines(keepends=True),
                    fromfile=file_path,
                    tofile=file_path
                ))
                diff_str = "".join(diff_lines)
                
                result.changes.append(FileChange(
                    file_path=file_path,
                    original_content_hash=orig_hash,
                    proposed_content_hash=prop_hash,
                    diff=diff_str
                ))
                result.files_changed.append(file_path)

                if not dry_run:
                    # Apply changes
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(proposed_content)
                        
                    # Validate Syntax
                    try:
                        ast.parse(proposed_content)
                    except SyntaxError as e:
                        # Rollback
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(original_content)
                        result.success = False
                        result.errors.append(f"Syntax error after transform in {file_path}: {e}. Rolled back.")
                        result.changes.pop()
                        result.files_changed.pop()
                        
    return result
