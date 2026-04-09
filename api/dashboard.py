from collections import Counter
from datetime import UTC, datetime

from domain.models import AgentResult, FactoryRunResult


def render_dashboard() -> str:
    return """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>AI Software Factory Control Room</title>
      <link rel="preconnect" href="https://images.unsplash.com">
      <link rel="stylesheet" href="/static/ui/dashboard.css">
      <script defer src="/static/ui/dashboard.js"></script>
    </head>
    <body>
      <div class="shell">
        <header class="command-bar">
          <a class="brand" href="/">
            <span class="brand-mark">AF</span>
            <span>
              <strong>Autonomous Factory</strong>
              <small id="snapshot-age">Waiting for telemetry</small>
            </span>
          </a>
          <nav class="command-links" aria-label="Factory links">
            <a href="/docs">API Docs</a>
            <a href="/metrics">Metrics</a>
            <a href="/health">Health</a>
          </nav>
        </header>

        <main>
          <section class="mission-deck" aria-label="Factory mission control">
            <div class="mission-copy">
              <p class="eyebrow">LIVE SOFTWARE PRODUCTION CELL</p>
              <h1>Design. Generate. Review. Repair. Ship.</h1>
              <p class="mission-text">
                Five autonomous agents turn product intent into runnable services, delivery manifests,
                code analysis, repair reports, and operational telemetry.
              </p>
              <div class="action-row">
                <a class="primary-action" href="/docs#/default/run_factory_factory_runs_post">Launch a Run</a>
                <button class="secondary-action" id="refresh-now" type="button">Refresh Telemetry</button>
              </div>
            </div>

            <div class="mission-visual" aria-label="Animated factory graph">
              <canvas id="factory-map"></canvas>
              <img
                src="https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=1200&q=80"
                alt="Close view of illuminated electronics inside an automation system"
              >
              <div class="visual-readout">
                <span>Pipeline</span>
                <strong id="pipeline-readout">standing by</strong>
              </div>
            </div>
          </section>

          <section class="metrics-strip" aria-label="Factory metrics">
            <article>
              <span>Total Runs</span>
              <strong id="metric-runs">0</strong>
            </article>
            <article>
              <span>Agent Executions</span>
              <strong id="metric-agents">0</strong>
            </article>
            <article>
              <span>Success Rate</span>
              <strong id="metric-success">0%</strong>
            </article>
            <article>
              <span>Latest Runtime</span>
              <strong id="metric-runtime">0.00s</strong>
            </article>
          </section>

          <section class="operations-grid">
            <div class="panel agent-panel">
              <div class="panel-heading">
                <p class="eyebrow">AGENT SWARM</p>
                <h2>Run Sequence</h2>
              </div>
              <ol class="agent-rail" id="agent-rail"></ol>
            </div>

            <div class="panel">
              <div class="panel-heading horizontal">
                <div>
                  <p class="eyebrow">DEPLOYMENT FLOOR</p>
                  <h2>Recent Runs</h2>
                </div>
                <span class="status-pill" id="fleet-status">unknown</span>
              </div>
              <div class="run-list" id="run-list"></div>
            </div>
          </section>

          <section class="panel terminal-panel" aria-label="Factory logs">
            <div class="panel-heading horizontal">
              <div>
                <p class="eyebrow">BLACKBOX STREAM</p>
                <h2>Agent Logs</h2>
              </div>
              <span id="event-count">0 events</span>
            </div>
            <pre id="log-stream" class="terminal-output">Telemetry stream will appear after the next refresh.</pre>
          </section>
        </main>
      </div>
    </body>
    </html>
    """


def dashboard_snapshot(
    *,
    runs: list[FactoryRunResult],
    agents: list[AgentResult],
) -> dict:
    total_runs = len(runs)
    successful_runs = sum(1 for run in runs if run.status.value == "succeeded")
    latest = runs[0] if runs else None
    latest_runtime = sum(agent.runtime_seconds for agent in latest.agent_results) if latest else 0.0
    status_counts = Counter(run.status.value for run in runs)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {
            "total_runs": total_runs,
            "agent_executions": len(agents),
            "success_rate": successful_runs / total_runs if total_runs else 0,
            "latest_runtime_seconds": latest_runtime,
            "run_status_counts": dict(status_counts),
        },
        "runs": [_run_payload(run) for run in runs],
        "agents": [_agent_payload(agent) for agent in agents],
    }


def _run_payload(run: FactoryRunResult) -> dict:
    return {
        "id": run.id,
        "project": run.spec.name,
        "summary": run.spec.summary,
        "status": run.status.value,
        "output_dir": run.output_dir,
        "created_at": run.created_at.isoformat(),
        "issue_count": len(run.scan_report.issues) if run.scan_report else 0,
        "deployment_ready": bool(run.deployment.get("ready")),
        "agents": [_agent_payload(agent) for agent in run.agent_results],
    }


def _agent_payload(agent: AgentResult) -> dict:
    return {
        "run_id": agent.run_id,
        "name": agent.agent_name.value,
        "status": agent.status.value,
        "runtime_seconds": agent.runtime_seconds,
        "logs": agent.logs,
        "error": agent.error,
        "finished_at": agent.finished_at.isoformat(),
    }

