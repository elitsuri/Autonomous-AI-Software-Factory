import json
import re
from dataclasses import dataclass
from pathlib import Path

from domain.models import ScanReport
from services.analyzer import CodeAnalyzer


@dataclass
class RepairSummary:
    changed_files: list[str]
    report_path: str


class SelfImprovementService:
    def __init__(self, analyzer: CodeAnalyzer) -> None:
        self.analyzer = analyzer

    async def inspect_and_repair(self, root: Path, *, apply: bool) -> tuple[ScanReport, RepairSummary]:
        root = root.resolve()
        report_before = await self.analyzer.scan(root)
        changed_files: list[str] = []

        if apply:
            changed_files.extend(self._repair_blocking_sleep(root, report_before))

        report_after = await self.analyzer.scan(root)
        factory_dir = root / ".factory"
        factory_dir.mkdir(exist_ok=True)
        report_path = factory_dir / "analysis-report.json"
        report_path.write_text(report_after.model_dump_json(indent=2), encoding="utf-8")
        return report_after, RepairSummary(changed_files=sorted(set(changed_files)), report_path=str(report_path))

    def remember_bug_signature(self, root: Path, signature: str, resolution: str) -> Path:
        factory_dir = root.resolve() / ".factory"
        factory_dir.mkdir(exist_ok=True)
        path = factory_dir / "bug-signatures.json"
        signatures = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        signatures.append({"signature": signature, "resolution": resolution})
        path.write_text(json.dumps(signatures[-100:], indent=2), encoding="utf-8")
        return path

    def _repair_blocking_sleep(self, root: Path, report: ScanReport) -> list[str]:
        changed: list[str] = []
        for issue in report.issues:
            if issue.rule != "async.blocking_sleep":
                continue
            path = root / issue.path
            source = path.read_text(encoding="utf-8")
            repaired = source.replace("time.sleep(", "await asyncio.sleep(")
            if repaired != source and "import asyncio" not in repaired:
                repaired = self._add_asyncio_import(repaired)
            if repaired != source:
                path.write_text(repaired, encoding="utf-8")
                changed.append(issue.path)
        return changed

    def _add_asyncio_import(self, source: str) -> str:
        import_lines = list(re.finditer(r"^(import .+|from .+ import .+)$", source, flags=re.MULTILINE))
        if not import_lines:
            return "import asyncio\n\n" + source
        insertion = import_lines[-1].end()
        return source[:insertion] + "\nimport asyncio" + source[insertion:]

