const agentNames = ["architect", "developer", "reviewer", "debugger", "devops"];
const canvas = document.querySelector("#factory-map");
const context = canvas.getContext("2d");
const state = {
  snapshot: null,
  nodes: [],
  pulses: [],
  lastFrame: performance.now(),
};

const elements = {
  snapshotAge: document.querySelector("#snapshot-age"),
  pipelineReadout: document.querySelector("#pipeline-readout"),
  metricRuns: document.querySelector("#metric-runs"),
  metricAgents: document.querySelector("#metric-agents"),
  metricSuccess: document.querySelector("#metric-success"),
  metricRuntime: document.querySelector("#metric-runtime"),
  agentRail: document.querySelector("#agent-rail"),
  runList: document.querySelector("#run-list"),
  logStream: document.querySelector("#log-stream"),
  fleetStatus: document.querySelector("#fleet-status"),
  eventCount: document.querySelector("#event-count"),
  refreshNow: document.querySelector("#refresh-now"),
};

function resizeCanvas() {
  const bounds = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(bounds.width * ratio));
  canvas.height = Math.max(1, Math.floor(bounds.height * ratio));
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  layoutNodes(bounds.width, bounds.height);
}

function layoutNodes(width, height) {
  state.nodes = agentNames.map((name, index) => {
    const progress = agentNames.length === 1 ? 0.5 : index / (agentNames.length - 1);
    return {
      name,
      x: 80 + progress * Math.max(220, width - 160),
      y: height * (0.34 + Math.sin(index * 1.7) * 0.12),
      radius: 25 + (index % 2) * 7,
    };
  });
}

function statusForAgent(name) {
  const latestRun = state.snapshot?.runs?.[0];
  const agent = latestRun?.agents?.find((entry) => entry.name === name);
  return agent?.status || "pending";
}

function drawFactoryMap(now) {
  const bounds = canvas.getBoundingClientRect();
  context.clearRect(0, 0, bounds.width, bounds.height);
  drawGrid(bounds, now);
  drawLinks(now);
  drawPulses(now);
  drawNodes(now);
  requestAnimationFrame(drawFactoryMap);
}

function drawGrid(bounds, now) {
  context.save();
  context.strokeStyle = "rgba(216, 226, 220, 0.08)";
  context.lineWidth = 1;
  const offset = (now / 40) % 48;
  for (let x = -offset; x < bounds.width + 48; x += 48) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, bounds.height);
    context.stroke();
  }
  for (let y = 0; y < bounds.height; y += 48) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(bounds.width, y);
    context.stroke();
  }
  context.restore();
}

function drawLinks(now) {
  context.save();
  for (let index = 0; index < state.nodes.length - 1; index += 1) {
    const start = state.nodes[index];
    const end = state.nodes[index + 1];
    const gradient = context.createLinearGradient(start.x, start.y, end.x, end.y);
    gradient.addColorStop(0, "rgba(46, 229, 157, 0.18)");
    gradient.addColorStop(0.5 + Math.sin(now / 450 + index) * 0.25, "rgba(255, 209, 102, 0.85)");
    gradient.addColorStop(1, "rgba(255, 98, 104, 0.18)");
    context.strokeStyle = gradient;
    context.lineWidth = 3;
    context.beginPath();
    context.moveTo(start.x, start.y);
    context.bezierCurveTo(start.x + 80, start.y - 95, end.x - 80, end.y + 95, end.x, end.y);
    context.stroke();
  }
  context.restore();
}

function drawPulses(now) {
  if (state.pulses.length < 14 && Math.random() > 0.78) {
    state.pulses.push({ lane: Math.floor(Math.random() * 4), born: now, life: 2400 + Math.random() * 1600 });
  }

  context.save();
  state.pulses = state.pulses.filter((pulse) => now - pulse.born < pulse.life);
  for (const pulse of state.pulses) {
    const progress = (now - pulse.born) / pulse.life;
    const start = state.nodes[pulse.lane];
    const end = state.nodes[pulse.lane + 1];
    if (!start || !end) {
      continue;
    }
    const x = start.x + (end.x - start.x) * progress;
    const y = start.y + (end.y - start.y) * progress + Math.sin(progress * Math.PI) * -70;
    context.fillStyle = "rgba(255, 209, 102, 0.95)";
    context.beginPath();
    context.arc(x, y, 4, 0, Math.PI * 2);
    context.fill();
  }
  context.restore();
}

function drawNodes(now) {
  context.save();
  context.font = "700 12px ui-sans-serif, system-ui, Arial";
  context.textAlign = "center";
  context.textBaseline = "middle";

  for (const node of state.nodes) {
    const status = statusForAgent(node.name);
    const color = status === "failed" ? "#ff6268" : status === "succeeded" ? "#2ee59d" : "#ffd166";
    const breath = Math.sin(now / 360 + node.radius) * 3;

    context.fillStyle = "rgba(7, 9, 9, 0.95)";
    context.strokeStyle = color;
    context.lineWidth = 3;
    context.beginPath();
    context.arc(node.x, node.y, node.radius + breath, 0, Math.PI * 2);
    context.fill();
    context.stroke();

    context.fillStyle = color;
    context.fillText(node.name.toUpperCase().slice(0, 3), node.x, node.y);
  }
  context.restore();
}

async function refreshSnapshot() {
  try {
    const response = await fetch("/dashboard/snapshot", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`snapshot ${response.status}`);
    }
    state.snapshot = await response.json();
    renderSnapshot(state.snapshot);
  } catch (error) {
    elements.snapshotAge.textContent = "Telemetry unavailable";
    elements.pipelineReadout.textContent = error.message;
  }
}

function renderSnapshot(snapshot) {
  const metrics = snapshot.metrics;
  elements.snapshotAge.textContent = `Telemetry refreshed ${new Date(snapshot.generated_at).toLocaleTimeString()}`;
  elements.metricRuns.textContent = metrics.total_runs.toString();
  elements.metricAgents.textContent = metrics.agent_executions.toString();
  elements.metricSuccess.textContent = `${Math.round(metrics.success_rate * 100)}%`;
  elements.metricRuntime.textContent = `${metrics.latest_runtime_seconds.toFixed(2)}s`;
  elements.fleetStatus.textContent = metrics.run_status_counts.failed ? "attention required" : "factory nominal";

  const latestRun = snapshot.runs[0];
  elements.pipelineReadout.textContent = latestRun
    ? `${latestRun.project} :: ${latestRun.status} :: ${latestRun.issue_count} issues`
    : "standing by";

  renderAgents(latestRun?.agents || []);
  renderRuns(snapshot.runs);
  renderLogs(snapshot);
}

function renderAgents(agents) {
  elements.agentRail.replaceChildren(
    ...agentNames.map((name) => {
      const agent = agents.find((entry) => entry.name === name);
      const item = document.createElement("li");
      item.dataset.status = agent?.status || "pending";
      item.innerHTML = `
        <h3>${escapeHtml(name)}</h3>
        <p>${agent ? escapeHtml(agent.logs.at(-1) || "Agent completed.") : "Waiting for the next factory run."}</p>
        <div class="agent-meta">
          <span>${escapeHtml(agent?.status || "pending")}</span>
          <span>${formatSeconds(agent?.runtime_seconds || 0)}</span>
        </div>
      `;
      return item;
    })
  );
}

function renderRuns(runs) {
  if (!runs.length) {
    const empty = document.createElement("article");
    empty.className = "run-card";
    empty.innerHTML = "<h3>No factory runs yet</h3><p>Launch a run from the API docs and this room will light up.</p>";
    elements.runList.replaceChildren(empty);
    return;
  }

  elements.runList.replaceChildren(
    ...runs.slice(0, 8).map((run) => {
      const card = document.createElement("article");
      card.className = "run-card";
      card.dataset.status = run.status;
      card.innerHTML = `
        <h3>${escapeHtml(run.project)}</h3>
        <p>${escapeHtml(run.summary)}</p>
        <div class="run-meta">
          <span>${escapeHtml(run.status)}</span>
          <span>${run.deployment_ready ? "deployment ready" : "deployment pending"}</span>
          <span>${run.issue_count} issues</span>
          <span>${new Date(run.created_at).toLocaleString()}</span>
        </div>
      `;
      return card;
    })
  );
}

function renderLogs(snapshot) {
  const lines = [];
  for (const run of snapshot.runs.slice(0, 4)) {
    lines.push(`$ factory run ${run.project} --status ${run.status}`);
    for (const agent of run.agents) {
      for (const log of agent.logs) {
        lines.push(`[${agent.name.padEnd(9)}] ${log}`);
      }
    }
    lines.push("");
  }
  elements.logStream.textContent = lines.join("\n") || "No logs captured yet.";
  elements.eventCount.textContent = `${lines.filter(Boolean).length} events`;
}

function formatSeconds(value) {
  return `${value.toFixed(3)}s`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return entities[character];
  });
}

window.addEventListener("resize", resizeCanvas);
elements.refreshNow.addEventListener("click", refreshSnapshot);
resizeCanvas();
refreshSnapshot();
setInterval(refreshSnapshot, 8000);
requestAnimationFrame(drawFactoryMap);

