const API_BASE = window.location.port === "3000"
  ? `${window.location.protocol}//${window.location.hostname}:8080`
  : "";

const api = async (path, options = {}) => {
  const response = await fetch(API_BASE + path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
};

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let flameChart;

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

function buildFlameData(root) {
  const data = [];
  let maxDepth = 0;

  const walk = (node, start, depth, parentPath) => {
    const path = parentPath ? `${parentPath} → ${node.name}` : node.name;
    maxDepth = Math.max(maxDepth, depth);
    data.push({
      name: node.name,
      samples: node.value,
      path,
      value: [start, start + node.value, depth]
    });

    let childStart = start;
    (node.children || []).forEach(child => {
      walk(child, childStart, depth + 1, path);
      childStart += child.value;
    });
  };

  let start = 0;
  (root.children || []).forEach(child => {
    walk(child, start, 0, "");
    start += child.value;
  });
  return { data, maxDepth };
}

function renderFlamegraph(root) {
  const container = document.querySelector("#flamegraph");
  const { data, maxDepth } = buildFlameData(root);
  container.style.height = `${Math.max(280, (maxDepth + 1) * 36 + 80)}px`;
  if (!flameChart) {
    container.textContent = "";
    flameChart = echarts.init(container);
  } else {
    flameChart.resize();
  }

  flameChart.setOption({
    animationDurationUpdate: 300,
    grid: { left: 12, right: 12, top: 20, bottom: 34 },
    tooltip: {
      formatter: params => {
        const item = params.data;
        const percent = (item.samples / root.value * 100).toFixed(2);
        return `<strong>${esc(item.name)}</strong><br>${item.samples} samples (${percent}%)<br><span class="tooltip-path">${esc(item.path)}</span>`;
      }
    },
    xAxis: { min: 0, max: root.value, show: false },
    yAxis: { min: -0.5, max: maxDepth + 0.5, show: false },
    dataZoom: [
      { type: "inside", xAxisIndex: 0, filterMode: "none" },
      { type: "slider", xAxisIndex: 0, filterMode: "none", height: 18, bottom: 4 }
    ],
    series: [{
      type: "custom",
      coordinateSystem: "cartesian2d",
      data,
      encode: { x: [0, 1], y: 2 },
      renderItem(params, api) {
        const start = api.coord([api.value(0), api.value(2)]);
        const end = api.coord([api.value(1), api.value(2)]);
        const bandHeight = api.size([0, 1])[1];
        const shape = echarts.graphic.clipRectByRect({
          x: start[0] + 1,
          y: start[1] - bandHeight * 0.42,
          width: Math.max(1, end[0] - start[0] - 2),
          height: bandHeight * 0.84
        }, params.coordSys);
        if (!shape) return null;

        const hue = 22 + (api.value(2) * 7 + params.dataIndex * 3) % 24;
        const children = [{
          type: "rect",
          shape,
          style: { fill: `hsl(${hue} 92% 68%)`, stroke: "#d97706", lineWidth: 0.7 }
        }];
        if (shape.width > 48) {
          children.push({
            type: "text",
            style: {
              x: shape.x + 6,
              y: shape.y + shape.height / 2,
              text: data[params.dataIndex].name,
              width: shape.width - 12,
              overflow: "truncate",
              ellipsis: "…",
              fill: "#4a2508",
              font: "12px sans-serif",
              verticalAlign: "middle"
            }
          });
        }
        return { type: "group", children };
      }
    }]
  }, true);
}

async function showTask(id) {
  const task = await api(`/api/v1/tasks/${id}`);
  const panel = document.querySelector("#result-panel");
  panel.hidden = false;
  document.querySelector("#timeline").textContent = task.events.map(e => `${e.to_status}: ${e.reason}`).join(" → ");
  if (!task.result) {
    flameChart?.dispose();
    flameChart = undefined;
    document.querySelector("#flamegraph").textContent = "任务尚未完成";
    document.querySelector("#metrics").innerHTML = "";
    document.querySelector("#top-functions").innerHTML = "";
    return;
  }
  renderMetrics(task.result.metrics || task.performance_data || {});
  renderFlamegraph(task.result.flamegraph);
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
window.addEventListener("resize", () => flameChart?.resize());
load().catch(error => document.querySelector("#message").textContent = error.message);
setInterval(() => load().catch(() => {}), 3000);
