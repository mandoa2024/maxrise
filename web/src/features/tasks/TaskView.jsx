import React, { useEffect, useState } from "react";

import EbpfProbeSelector from "../../components/EbpfProbeSelector.jsx";
import { ActivityIcon, PlayIcon } from "../../components/Icons.jsx";
import ProfileVisualization from "../../components/ProfileVisualization.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { COLLECTORS } from "../../config/profiling.js";
import { api } from "../../lib/api.js";
import { formatTimestamp } from "../../lib/format.js";

function TaskForm({ agents, onCreated }) {
  const [agentId, setAgentId] = useState("");
  const [pid, setPid] = useState(1);
  const [duration, setDuration] = useState(5);
  const [sampleRate, setSampleRate] = useState(99);
  const [collector, setCollector] = useState("perf");
  const [ebpfProbes, setEbpfProbes] = useState(["vfs_read"]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!agentId && agents.length) setAgentId(agents[0].id);
  }, [agentId, agents]);

  async function submit(event) {
    event.preventDefault();
    try {
      await api("/api/v1/tasks", {
        method: "POST",
        body: JSON.stringify({
          agent_id: agentId,
          pid: Number(pid),
          duration_seconds: Number(duration),
          sample_rate: Number(sampleRate),
          collector,
          ebpf_probes: ebpfProbes,
        }),
      });
      setMessage("任务已创建");
      await onCreated();
    } catch (error) {
      setMessage(error.message);
    }
  }

  const fieldClass =
    "px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary";

  return (
    <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-6 shadow-xl">
      <div className="mb-4 flex items-center gap-3">
        <div className="rounded-lg border border-primary/50 bg-primary/20 p-3">
          <ActivityIcon />
        </div>
        <div>
          <h2 className="m-0 text-xl font-semibold text-white">创建 CPU 采样任务</h2>
          <p className="m-0 text-sm text-slate-400">对目标进程进行性能分析</p>
        </div>
      </div>
      <form onSubmit={submit} className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">Agent</span>
          <select className={fieldClass} value={agentId} onChange={(e) => setAgentId(e.target.value)} required>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>{agent.name} ({agent.status})</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">采集器</span>
          <select className={fieldClass} value={collector} onChange={(e) => setCollector(e.target.value)}>
            {COLLECTORS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        {collector === "ebpf" && <EbpfProbeSelector value={ebpfProbes} onChange={setEbpfProbes} />}
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">目标 PID</span>
          <input className={fieldClass} type="number" min="1" value={pid} onChange={(e) => setPid(e.target.value)} required />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">采样时长（秒）</span>
          <input className={fieldClass} type="number" min="1" max="300" value={duration} onChange={(e) => setDuration(e.target.value)} required />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">采样率（Hz）</span>
          <input className={fieldClass} type="number" min="1" max="999" value={sampleRate} onChange={(e) => setSampleRate(e.target.value)} required />
        </label>
        <button className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-secondary px-4 py-2 text-white" type="submit">
          <PlayIcon /> 开始采样
        </button>
      </form>
      {message && <p className="mt-3 text-sm text-slate-300">{message}</p>}
    </section>
  );
}

function TaskTable({ tasks, onSelect }) {
  return (
    <section className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/30 p-6 shadow-xl">
      <h2 className="mb-4 text-lg font-semibold text-white">任务列表</h2>
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700 text-left text-sm text-slate-300">
            <th className="px-4 py-3">ID</th><th>PID</th><th>采集器</th><th>状态</th><th>原因</th><th>时间</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id} onClick={() => onSelect(task.id)} className="cursor-pointer border-b border-slate-700/50 text-sm text-slate-400 hover:bg-slate-700/30">
              <td className="px-4 py-3 font-mono text-slate-300">{task.id.slice(0, 8)}</td>
              <td>{task.pid}</td><td>{task.collector}</td>
              <td><StatusBadge value={task.status} /></td>
              <td>{task.status_reason}</td><td>{formatTimestamp(task.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!tasks.length && <p className="py-6 text-center text-slate-500">暂无任务</p>}
    </section>
  );
}

function ResultPanel({ task }) {
  if (!task) return null;
  return (
    <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-6 shadow-xl">
      <h2 className="mb-4 text-lg font-semibold text-white">分析结果</h2>
      {task.result ? (
        <ProfileVisualization result={task.result} collector={task.collector} />
      ) : (
        <div className="flex min-h-64 items-center justify-center rounded-lg border border-slate-700 bg-slate-800/50 text-slate-400">
          任务尚未完成，正在处理中...
        </div>
      )}
    </section>
  );
}

export default function TaskView({
  agents,
  tasks,
  selectedTask,
  onCreated,
  onSelectTask,
}) {
  return (
    <>
      <TaskForm agents={agents} onCreated={onCreated} />
      <TaskTable tasks={tasks} onSelect={onSelectTask} />
      <ResultPanel task={selectedTask} />
    </>
  );
}
