from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class FindingItem:
    fingerprint: str
    rule_id: str
    title: str
    category: str  # Vulnerability, Secret, Dependency, Quality, License
    severity: str  # Critical, High, Medium, Low, Informational
    confidence: str  # High, Medium, Low
    file_path: str
    line_number: Optional[int]
    message: str
    code_snippet: Optional[str] = None
    evidence: Optional[str] = None
    impact: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    classification: str = "Valid heuristic finding requiring manual verification"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "rule": self.rule_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "classification": self.classification,
            "file_path": self.file_path,
            "location": f"Line {self.line_number}" if self.line_number else "Repository",
            "line_number": self.line_number,
            "message": self.message,
            "description": self.message,
            "code_snippet": self.code_snippet,
            "evidence": self.evidence,
            "impact": self.impact,
            "remediation": self.remediation,
            "references": self.references
        }

@dataclass
class ToolCoverage:
    tool_name: str
    category: str
    status: str  # COMPLETED, PARTIAL, SKIPPED, FAILED
    duration_seconds: float
    files_scanned: int
    findings_count: int
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "category": self.category,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "files_scanned": self.files_scanned,
            "findings_count": self.findings_count,
            "error_message": self.error_message
        }

@dataclass
class ScanCoverage:
    overall_status: str  # COMPLETED, PARTIAL, FAILED
    tools: Dict[str, ToolCoverage] = field(default_factory=dict)
    files_examined: int = 0
    files_skipped: int = 0
    supported_languages: List[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    is_provisional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "tools": {k: v.to_dict() for k, v in self.tools.items()},
            "files_examined": self.files_examined,
            "files_skipped": self.files_skipped,
            "supported_languages": sorted(list(set(self.supported_languages))),
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "is_provisional": self.is_provisional
        }


def is_test_or_benchmark_path(file_path: Optional[str]) -> bool:
    """Returns True if the file path is part of test suites, benchmark datasets,
    mock corpora, or fixture directories rather than production application runtime."""
    if not file_path:
        return False
    norm = file_path.replace("\\", "/").lower()
    parts = [p for p in norm.split("/") if p]
    filename = parts[-1] if parts else ""
    dirs = parts[:-1]

    test_dirs = {
        "tests", "test", "testing", "benchmark", "benchmarks", "benches", "bench",
        "fixtures", "fixture", "mocks", "mock", "spec", "specs",
        "testdata", "test-fixtures", "test_fixtures", "samples", "sample",
        "examples", "example", "__tests__", "__test__", "__mocks__",
        "e2e", "cypress", "playwright", "features", "unittests", "unittest"
    }
    for d in dirs:
        if d in test_dirs:
            return True
        if (
            d.endswith(".tests")
            or d.endswith(".unittests")
            or d.endswith("_tests")
            or d.endswith("-tests")
            or d.endswith(".test")
            or d.endswith(".unittest")
            or d.endswith("_test")
            or d.endswith("-test")
        ):
            return True

    if filename.startswith("test_") or filename.startswith("mock_") or filename.startswith("fixture_"):
        return True
    if (
        filename.endswith("_test.py")
        or filename.endswith(".test.ts")
        or filename.endswith(".test.js")
        or filename.endswith(".spec.ts")
        or filename.endswith(".spec.js")
        or filename.endswith(".test.tsx")
        or filename.endswith(".spec.tsx")
        or filename.endswith(".test.jsx")
        or filename.endswith(".spec.jsx")
        or filename.endswith("_test.go")
        or filename.endswith("test.java")
        or filename.endswith("tests.java")
        or filename.endswith("testcase.java")
        or filename.endswith("test.kt")
        or filename.endswith("tests.kt")
        or filename.endswith("tests.cs")
        or filename.endswith("test.cs")
        or filename.endswith("_spec.rb")
        or filename.endswith("_test.rb")
        or filename.endswith("test.php")
        or filename.endswith("tests.php")
    ):
        return True
    if filename in {"test.py", "tests.py", "fixtures.py", "fixture.py", "conftest.py", "corpus.py", "test_fixtures.py"}:
        return True

    return False


