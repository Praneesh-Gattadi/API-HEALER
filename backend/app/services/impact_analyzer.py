import os
import libcst as cst
from typing import List, Set
from app.models.provider import ImpactAnalysis, EvidenceStrength
from app.models.diff_result import DiffResult, ChangeType

class EvidenceVisitor(cst.CSTVisitor):
    def __init__(self, target_fields: Set[str], target_endpoints: Set[str]):
        super().__init__()
        self.target_fields = target_fields
        self.target_endpoints = target_endpoints
        
        self.has_strong_evidence = False
        self.has_weak_evidence = False
        self.details = []

    def visit_Arg(self, node: cst.Arg):
        # Keyword arguments: user_id=...
        if node.keyword and node.keyword.value in self.target_fields:
            self.has_strong_evidence = True
            self.details.append(f"Strong evidence: keyword argument '{node.keyword.value}' used")

    def visit_Attribute(self, node: cst.Attribute):
        # Attribute access: obj.user_id
        if node.attr.value in self.target_fields:
            self.has_strong_evidence = True
            self.details.append(f"Strong evidence: attribute '{node.attr.value}' accessed")

    def visit_DictElement(self, node: cst.DictElement):
        # Dict key: {"user_id": ...}
        if isinstance(node.key, cst.SimpleString):
            val = node.key.value.strip("\"'")
            if val in self.target_fields:
                self.has_strong_evidence = True
                self.details.append(f"Strong evidence: dict key '{val}' used")

    def visit_SubscriptElement(self, node: cst.SubscriptElement):
        # Dict subscript: d["user_id"]
        if isinstance(node.slice, cst.Index) and isinstance(node.slice.value, cst.SimpleString):
            val = node.slice.value.value.strip("\"'")
            if val in self.target_fields:
                self.has_strong_evidence = True
                self.details.append(f"Strong evidence: dict subscript '{val}' used")

    def visit_AnnAssign(self, node: cst.AnnAssign):
        # Class attribute / Pydantic field: user_id: str
        if isinstance(node.target, cst.Name) and node.target.value in self.target_fields:
            self.has_strong_evidence = True
            self.details.append(f"Strong evidence: class field '{node.target.value}' defined")

    def visit_SimpleString(self, node: cst.SimpleString):
        val = node.value.strip("\"'")
        # Check endpoints
        for endpoint in self.target_endpoints:
            if endpoint in val:
                self.has_strong_evidence = True
                self.details.append(f"Strong evidence: endpoint URL '{endpoint}' used in string")
        # Check fields
        for field in self.target_fields:
            if field in val:
                # Standalone string is weak evidence for a field, unless caught by dict key/subscript
                self.has_weak_evidence = True
                self.details.append(f"Weak evidence: string literal containing '{field}' found")

    # Comments are not easily visited as nodes in CST unless we inspect Comment nodes directly,
    # but they are attached to EmptyLine or TrailingWhitespace. We'll skip comments for simplicity MVP,
    # or just rely on SimpleString as weak evidence.

class ImpactAnalyzer:
    @classmethod
    def analyze(cls, repository_root: str, diff_result: DiffResult) -> ImpactAnalysis:
        target_fields = set()
        target_endpoints = set()

        for change in diff_result.changes:
            if change.type in (ChangeType.endpoint_removed, ChangeType.endpoint_added, ChangeType.method_removed):
                # path is the endpoint, e.g. /users
                target_endpoints.add(change.path.split(" ")[-1])
            else:
                # path is usually like "components.schemas.User.properties.user_id"
                field = change.path.split(".")[-1]
                target_fields.add(field)

        if not target_fields and not target_endpoints:
            return ImpactAnalysis(evidence_strength=EvidenceStrength.NONE, details=[])

        visitor = EvidenceVisitor(target_fields, target_endpoints)

        for root, _, files in os.walk(repository_root):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            source = f.read()
                        tree = cst.parse_module(source)
                        tree.visit(visitor)
                    except Exception:
                        pass # Ignore parsing errors in impact analyzer for MVP

        if visitor.has_strong_evidence:
            return ImpactAnalysis(
                evidence_strength=EvidenceStrength.STRONG,
                details=list(set(visitor.details))
            )
        elif visitor.has_weak_evidence:
            return ImpactAnalysis(
                evidence_strength=EvidenceStrength.WEAK,
                details=list(set(visitor.details))
            )
        else:
            return ImpactAnalysis(
                evidence_strength=EvidenceStrength.NONE,
                details=["No references found in repository"]
            )
