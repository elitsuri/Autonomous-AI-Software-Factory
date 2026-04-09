from datetime import UTC, datetime

from api.dashboard import dashboard_snapshot, render_dashboard
from domain.models import AgentName, AgentResult, AgentStatus, FactoryRunResult, ProjectSpec


def test_render_dashboard_references_static_gui_bundle() -> None:
    html = render_dashboard()

    assert "AI Software Factory Control Room" in html
    assert "/static/ui/dashboard.css" in html
    assert "/static/ui/dashboard.js" in html
    assert "factory-map" in html


def test_dashboard_snapshot_summarizes_runs_and_agents() -> None:
    now = datetime.now(UTC)
    agent = AgentResult(
        run_id="agent-1",
        agent_name=AgentName.ARCHITECT,
        status=AgentStatus.SUCCEEDED,
        input={},
        output={},
        logs=["architect: started", "architect: succeeded"],
        runtime_seconds=0.25,
        started_at=now,
        finished_at=now,
    )
    run = FactoryRunResult(
        spec=ProjectSpec(name="ops-room", summary="Operations room for factory telemetry."),
        output_dir="/tmp/ops-room",
        status=AgentStatus.SUCCEEDED,
        agent_results=[agent],
        deployment={"ready": True},
    )

    snapshot = dashboard_snapshot(runs=[run], agents=[agent])

    assert snapshot["metrics"]["total_runs"] == 1
    assert snapshot["metrics"]["agent_executions"] == 1
    assert snapshot["metrics"]["success_rate"] == 1
    assert snapshot["runs"][0]["project"] == "ops-room"
    assert snapshot["runs"][0]["agents"][0]["logs"][-1] == "architect: succeeded"

