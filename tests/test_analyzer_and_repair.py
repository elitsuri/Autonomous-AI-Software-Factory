from pathlib import Path

import pytest

from domain.models import Severity
from services.analyzer import CodeAnalyzer
from services.self_improvement import SelfImprovementService


@pytest.mark.asyncio
async def test_analyzer_detects_async_blocking_sleep_and_repair_fixes_it(tmp_path: Path) -> None:
    module = tmp_path / "service.py"
    module.write_text(
        "import time\n\n"
        "async def handler():\n"
        "    time.sleep(1)\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )

    analyzer = CodeAnalyzer()
    report = await analyzer.scan(tmp_path)

    assert report.has_blockers
    assert [(issue.rule, issue.severity) for issue in report.issues] == [("async.blocking_sleep", Severity.HIGH)]

    repaired_report, summary = await SelfImprovementService(analyzer).inspect_and_repair(tmp_path, apply=True)

    repaired_source = module.read_text(encoding="utf-8")
    assert "import asyncio" in repaired_source
    assert "await asyncio.sleep(1)" in repaired_source
    assert summary.changed_files == ["service.py"]
    assert Path(summary.report_path).exists()
    assert not repaired_report.has_blockers


def test_self_improvement_remembers_bug_signatures(tmp_path: Path) -> None:
    improver = SelfImprovementService(CodeAnalyzer())

    path = improver.remember_bug_signature(tmp_path, "TypeError: bad operand", "Validate numeric input")

    assert path.exists()
    assert "Validate numeric input" in path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_analyzer_reports_parse_error(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    report = await CodeAnalyzer().scan(tmp_path)

    assert report.scanned_files == 1
    assert report.issues[0].rule == "python.parse_error"
    assert report.issues[0].severity == Severity.HIGH


@pytest.mark.asyncio
async def test_analyzer_reports_observability_and_exception_risks(tmp_path: Path) -> None:
    (tmp_path / "risk.py").write_text(
        "def handler():\n"
        "    try:\n"
        "        print('debug')\n"
        "    except Exception:\n"
        "        return 'hidden'\n",
        encoding="utf-8",
    )

    report = await CodeAnalyzer().scan(tmp_path)

    assert {issue.rule for issue in report.issues} == {"observability.print", "exception.too_broad"}
