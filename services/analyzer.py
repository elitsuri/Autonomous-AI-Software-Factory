import ast
from pathlib import Path

from core.config import Settings
from domain.models import CodeIssue, ScanReport, Severity


class CodeAnalyzer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    async def scan(self, root: Path) -> ScanReport:
        root = root.resolve()
        issues: list[CodeIssue] = []
        scanned_files = 0

        for path in self._python_files(root):
            if self._is_too_large(path):
                issues.append(
                    CodeIssue(
                        path=str(path.relative_to(root)),
                        line=1,
                        rule="file.too_large_to_scan",
                        severity=Severity.MEDIUM,
                        message="File is larger than the configured scanner limit.",
                        suggestion="Split the module or increase MAX_SCAN_FILE_BYTES for trusted code.",
                    )
                )
                continue

            scanned_files += 1
            issues.extend(self._scan_python_file(path, root))

        return ScanReport(root=str(root), issues=issues, scanned_files=scanned_files)

    def _python_files(self, root: Path) -> list[Path]:
        ignored = {".venv", "venv", "__pycache__", ".git", ".pytest_cache", "node_modules"}
        return [
            path
            for path in root.rglob("*.py")
            if not any(part in ignored for part in path.parts)
        ]

    def _is_too_large(self, path: Path) -> bool:
        limit = self.settings.max_scan_file_bytes if self.settings else 750_000
        return path.stat().st_size > limit

    def _scan_python_file(self, path: Path, root: Path) -> list[CodeIssue]:
        rel_path = str(path.relative_to(root))
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (UnicodeDecodeError, SyntaxError) as exc:
            line = exc.lineno if isinstance(exc, SyntaxError) and exc.lineno else 1
            return [
                CodeIssue(
                    path=rel_path,
                    line=line,
                    rule="python.parse_error",
                    severity=Severity.HIGH,
                    message=f"Python parser failed: {exc}",
                    suggestion="Fix syntax before running generation, tests, or deployment.",
                )
            ]

        visitor = _IssueVisitor(rel_path)
        visitor.visit(tree)
        return visitor.issues


class _IssueVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.issues: list[CodeIssue] = []
        self._async_depth = 0

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._async_depth += 1
        self._check_function_size(node)
        self.generic_visit(node)
        self._async_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function_size(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.issues.append(
                self._issue(
                    node.lineno,
                    "exception.bare_except",
                    Severity.HIGH,
                    "Bare except hides cancellation, shutdown, and programming errors.",
                    "Catch a narrow exception type and log the failure context.",
                )
            )
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self.issues.append(
                self._issue(
                    node.lineno,
                    "exception.too_broad",
                    Severity.MEDIUM,
                    "Broad Exception handler can make recurring bugs harder to classify.",
                    "Catch expected exception classes and re-raise unexpected failures.",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        function_name = self._function_name(node.func)
        if self._async_depth and function_name == "time.sleep":
            self.issues.append(
                self._issue(
                    node.lineno,
                    "async.blocking_sleep",
                    Severity.HIGH,
                    "Blocking sleep was called from async code.",
                    "Use await asyncio.sleep(seconds) so the event loop keeps serving work.",
                )
            )
        if function_name == "print":
            self.issues.append(
                self._issue(
                    node.lineno,
                    "observability.print",
                    Severity.LOW,
                    "Direct print statement bypasses structured application logging.",
                    "Use a module logger so logs include timestamp, level, and request context.",
                )
            )
        self.generic_visit(node)

    def _check_function_size(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_lineno = node.end_lineno or node.lineno
        length = end_lineno - node.lineno + 1
        if length > 80:
            self.issues.append(
                self._issue(
                    node.lineno,
                    "maintainability.large_function",
                    Severity.MEDIUM,
                    f"Function {node.name!r} is {length} lines long.",
                    "Extract one cohesive branch into a named function or application service.",
                )
            )

    def _issue(
        self,
        line: int,
        rule: str,
        severity: Severity,
        message: str,
        suggestion: str,
    ) -> CodeIssue:
        return CodeIssue(
            path=self.path,
            line=line,
            rule=rule,
            severity=severity,
            message=message,
            suggestion=suggestion,
        )

    def _function_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = self._function_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

