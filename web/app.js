const API_BASE = window.location.port === "3000"
  ? `${window.location.protocol}//${window.location.hostname}:8080`
  : "";

const api = async (path, options = {}) => {
  const response = await fetch(API_BASE + path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
};

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function load() {
  const [agents, tasks, audits] = await Promise.all([
    api("/api/v1/agents"),
    api("/api/v1/tasks"),
    api("/api/v1/agents/audit-logs")
  ]);
  document.querySelector("#agent").innerHTML = agents.map(a => `<option value="${esc(a.id)}">${esc(a.name)} (${esc(a.status)})</option>`).join("");
  document.querySelector("#agents").innerHTML = agents.map(a => `<div class="card"><strong>${esc(a.name)}</strong><p><span class="status ${esc(a.status)}">${esc(a.status)}</span></p><small>${esc(a.hostname)}<br>${esc(a.last_heartbeat_at)}</small></div>`).join("") || "等待 Agent 注册";
  document.querySelector("#agent-audits").innerHTML = audits.map(a => `<tr><td>${esc(a.agent_id)}</td><td><span class="status ${esc(a.event)}">${esc(a.event)}</span></td><td>${esc(a.reason)}</td><td>${esc(a.created_at)}</td></tr>`).join("") || '<tr><td colspan="4">暂无审计日志</td></tr>';
  document.querySelector("#tasks").innerHTML = tasks.map(t => `<tr data-id="${esc(t.id)}"><td>${esc(t.id.slice(0, 8))}</td><td>${esc(t.pid)}</td><td><span class="status ${esc(t.status)}">${esc(t.status)}</span></td><td>${esc(t.status_reason)}</td><td>${esc(t.updated_at)}</td></tr>`).join("") || '<tr><td colspan="5">暂无任务</td></tr>';
  document.querySelectorAll("tr[data-id]").forEach(row => row.onclick = () => showTask(row.dataset.id));
  const done = tasks.find(t => t.status === "DONE");
  if (done) await showTask(done.id);
}

function formatKb(value) {
  if (value === null || value === undefined) return "N/A";
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} GB`;
  if (value >= 1024) return `${(value / 1024).toFixed(2)} MB`;
  return `${value} KB`;
}

function renderMetrics(metrics = {}) {
  const cpu = metrics.cpu || {};
  const memory = metrics.memory || {};
  const items = [
    ["CPU Collector", cpu.collector || "N/A"],
    ["CPU Event", cpu.event || "N/A"],
    ["Duration", cpu.duration_seconds ? `${cpu.duration_seconds}s` : "N/A"],
    ["Sample Rate", cpu.sample_rate_hz ? `${cpu.sample_rate_hz} Hz` : "N/A"],
    ["Stack Lines", cpu.collapsed_stack_lines ?? "N/A"],
    ["Memory RSS", formatKb(memory.rss_kb)],
    ["Memory VMS", formatKb(memory.vms_kb)],
    ["Peak RSS", formatKb(memory.peak_rss_kb)],
  ];
  document.querySelector("#metrics").innerHTML = items.map(([label, value]) => `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("");
}

function renderFallbackFlamegraph(root) {
  const levels = [];
  const walk = (node, start, depth, parentPath) => {
    levels[depth] ||= [];
    if (depth > 0) levels[depth].push(node);
    (node.children || []).forEach(child => walk(child, 0, depth + 1, ""));
  };
  walk(root, 0, 0, "");
  return levels.filter(level => level.length).reverse().map(level => `<div class="flame-row">${level.map(node => `<div class="flame-block" style="width:${Math.max(3, node.value / root.value * 100)}%" title="${esc(node.name)}: ${node.value}">${esc(node.name)} (${node.value})</div>`).join("")}</div>`).join("");
}

function renderFlamegraph(task) {
  const container = document.querySelector("#flamegraph");
  if (task.result.flamegraph_svg) {
    container.innerHTML = `<iframe title="CPU FlameGraph" sandbox="allow-scripts" srcdoc="${esc(task.result.flamegraph_svg)}"></iframe>`;
    return;
  }
  container.innerHTML = renderFallbackFlamegraph(task.result.flamegraph);
}

async function showTask(id) {
  const task = await api(`/api/v1/tasks/${id}`);
  const panel = document.querySelector("#result-panel");
  panel.hidden = false;
  document.querySelector("#timeline").textContent = task.events.map(e => `${e.to_status}: ${e.reason}`).join(" → ");
  if (!task.result) {
    document.querySelector("#flamegraph").textContent = "任务尚未完成";
    document.querySelector("#metrics").innerHTML = "";
    document.querySelector("#top-functions").innerHTML = "";
    return;
  }
  renderMetrics(task.result.metrics || task.performance_data || {});
  renderFlamegraph(task);
  document.querySelector("#top-functions").innerHTML = task.result.top_functions.map(f => `<tr><td>${esc(f.name)}</td><td>${f.samples} samples</td></tr>`).join("");
}

document.querySelector("#task-form").addEventListener("submit", async event => {
  event.preventDefault();
  const message = document.querySelector("#message");
  try {
    await api("/api/v1/tasks", { method: "POST", body: JSON.stringify({
      agent_id: document.querySelector("#agent").value,
      pid: Number(document.querySelector("#pid").value),
      duration_seconds: Number(document.querySelector("#duration").value),
      sample_rate: Number(document.querySelector("#rate").value),
      collector: "perf"
    }) });
    message.textContent = "任务已创建";
    await load();
  } catch (error) { message.textContent = error.message; }
});

document.querySelector("#refresh").onclick = load;
load().catch(error => document.querySelector("#message").textContent = error.message);
setInterval(() => load().catch(() => {}), 3000);
