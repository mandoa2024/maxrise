import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import EbpfProbeSelector from "../../components/EbpfProbeSelector.jsx";
import AttributionPanel from "../../components/AttributionPanel.jsx";
import { ClockIcon, PlayIcon, StopIcon } from "../../components/Icons.jsx";
import ProfileVisualization from "../../components/ProfileVisualization.jsx";
import StatusBadge from "../../components/StatusBadge.jsx";
import { COLLECTORS } from "../../config/profiling.js";
import { api } from "../../lib/api.js";
import { formatTimestamp } from "../../lib/format.js";

const WINDOW_MS = 5 * 60 * 1000;

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function timelineBounds(session, now) {
  const start = new Date(session?.started_at).getTime();
  const stoppedAt = new Date(session?.stopped_at).getTime();
  const end =
    session?.status === "STOPPED" && Number.isFinite(stoppedAt)
      ? stoppedAt
      : now;
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return null;
  }
  return { start, end };
}

function shortTime(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function ContinuousForm({ agents, onCreated }) {
  const [agentId, setAgentId] = useState("");
  const [pid, setPid] = useState(1);
  const [collector, setCollector] = useState("perf");
  const [ebpfProbes, setEbpfProbes] = useState(["vfs_read"]);
  const [sampleRate, setSampleRate] = useState(49);
  const [segmentSeconds, setSegmentSeconds] = useState(30);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!agentId && agents.length) setAgentId(agents[0].id);
  }, [agentId, agents]);

  async function submit(event) {
    event.preventDefault();
    try {
      await api("/api/v1/profile-sessions", {
        method: "POST",
        body: JSON.stringify({
          agent_id: agentId,
          pid: Number(pid),
          collector,
          ebpf_probes: ebpfProbes,
          sample_rate: Number(sampleRate),
          segment_seconds: Number(segmentSeconds),
        }),
      });
      setMessage("持续采样已启动");
      await onCreated();
    } catch (error) {
      setMessage(error.message);
    }
  }

  const fieldClass =
    "px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-accent";

  return (
    <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-6 shadow-xl">
      <div className="mb-4 flex items-center gap-3">
        <div className="rounded-lg border border-accent/50 bg-accent/20 p-3"><ClockIcon /></div>
        <div>
          <h2 className="m-0 text-xl font-semibold text-white">Continuous Profiling</h2>
          <p className="m-0 text-sm text-slate-400">持续性能监控和分析</p>
        </div>
      </div>
      <form onSubmit={submit} className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">Agent</span>
          <select className={fieldClass} value={agentId} onChange={(e) => setAgentId(e.target.value)} required>
            {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name} ({agent.status})</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">采集器</span>
          <select className={fieldClass} value={collector} onChange={(e) => setCollector(e.target.value)}>
            {COLLECTORS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        {collector === "ebpf" && <EbpfProbeSelector value={ebpfProbes} onChange={setEbpfProbes} accent="accent" />}
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">目标 PID</span>
          <input className={fieldClass} type="number" min="1" value={pid} onChange={(e) => setPid(e.target.value)} />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">低频采样率（Hz）</span>
          <input className={fieldClass} type="number" min="1" max="999" value={sampleRate} onChange={(e) => setSampleRate(e.target.value)} />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-sm text-slate-300">切片时长（秒）</span>
          <input className={fieldClass} type="number" min="1" max="300" value={segmentSeconds} onChange={(e) => setSegmentSeconds(e.target.value)} />
        </label>
        <button className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-accent to-orange-500 px-4 py-2 text-white" type="submit">
          <PlayIcon /> 启动
        </button>
      </form>
      {message && <p className="mt-3 text-sm text-slate-300">{message}</p>}
    </section>
  );
}

function SessionTable({ sessions, onSelect, onStop }) {
  return (
    <section className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/30 p-6 shadow-xl">
      <h2 className="mb-4 text-lg font-semibold text-white">持续采样 Sessions</h2>
      <table className="w-full">
        <thead><tr className="border-b border-slate-700 text-left text-sm text-slate-300">
          <th className="px-4 py-3">ID</th><th>PID</th><th>采集器</th><th>状态</th><th>开始时间</th><th>最新数据</th><th>操作</th>
        </tr></thead>
        <tbody>
          {sessions.map((session) => (
            <tr key={session.id} onClick={() => onSelect(session)} className="cursor-pointer border-b border-slate-700/50 text-sm text-slate-400 hover:bg-slate-700/30">
              <td className="px-4 py-3 font-mono text-slate-300">{session.id.slice(0, 8)}</td>
              <td>{session.pid}</td><td>{session.collector}</td><td><StatusBadge value={session.status} /></td>
              <td>{formatTimestamp(session.started_at)}</td><td>{formatTimestamp(session.last_segment_at)}</td>
              <td>{session.status === "RUNNING" && (
                <button type="button" onClick={(event) => { event.stopPropagation(); onStop(session.id); }} className="flex items-center gap-1 rounded border border-red-500/50 bg-red-500/20 px-3 py-1 text-red-400">
                  <StopIcon /> 停止
                </button>
              )}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!sessions.length && <p className="py-6 text-center text-slate-500">暂无持续采样 Session</p>}
    </section>
  );
}

function WindowPanel({ session }) {
  const timelineRef = useRef(null);
  const dragRef = useRef(null);
  const [segments, setSegments] = useState([]);
  const [segmentsSessionId, setSegmentsSessionId] = useState(null);
  const [windowStart, setWindowStart] = useState(null);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [attributions, setAttributions] = useState([]);
  const [attributionConfig, setAttributionConfig] = useState(null);
  const [now, setNow] = useState(Date.now());
  const bounds = useMemo(
    () =>
      segmentsSessionId === session?.id ? timelineBounds(session, now) : null,
    [now, segmentsSessionId, session],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadSegments() {
      if (!session) return;
      try {
        const nextSegments = await api(
          `/api/v1/profile-sessions/${session.id}/segments`,
        );
        if (!cancelled) {
          setSegments(nextSegments);
          setSegmentsSessionId(session.id);
          setMessage("");
        }
      } catch (error) {
        if (!cancelled) setMessage(error.message);
      }
    }

    async function loadAttributions() {
      if (!session) return;
      try {
        const [runs, config] = await Promise.all([
          api(`/api/v1/profile-sessions/${session.id}/attributions`),
          api("/api/v1/attribution/config"),
        ]);
        if (!cancelled) {
          setAttributions(runs);
          setAttributionConfig(config);
        }
      } catch {
        // Profiling remains usable if attribution is unavailable.
      }
    }

    setSegments([]);
    setSegmentsSessionId(null);
    setWindowStart(null);
    setResult(null);
    setMessage("");
    setAttributions([]);
    setNow(Date.now());
    loadSegments();
    loadAttributions();
    const timer = window.setInterval(loadSegments, 3000);
    const attributionTimer = window.setInterval(loadAttributions, 5000);
    const clock = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearInterval(attributionTimer);
      window.clearInterval(clock);
    };
  }, [session?.id]);

  const queryWindow = useCallback(
    async (start) => {
      if (!session || start === null) return;
      setLoading(true);
      try {
        const params = new URLSearchParams({
          from: new Date(start).toISOString(),
          to: new Date(start + WINDOW_MS).toISOString(),
        });
        setResult(
          await api(
            `/api/v1/profile-sessions/${session.id}/flamegraph?${params}`,
          ),
        );
        setMessage("");
      } catch (error) {
        setResult(null);
        setMessage(error.message);
      } finally {
        setLoading(false);
      }
    },
    [session],
  );

  useEffect(() => {
    if (!bounds || bounds.end - bounds.start < WINDOW_MS) return;
    setWindowStart((current) => {
      if (current !== null) {
        return clamp(current, bounds.start, bounds.end - WINDOW_MS);
      }
      const latestStart = bounds.end - WINDOW_MS;
      queryWindow(latestStart);
      return latestStart;
    });
  }, [bounds, queryWindow]);

  if (!session) return null;

  const ready = Boolean(bounds && bounds.end - bounds.start >= WINDOW_MS);
  const duration = bounds ? bounds.end - bounds.start : WINDOW_MS;
  const maxOffset = Math.max(0, duration - WINDOW_MS);
  const offset = bounds && windowStart !== null ? windowStart - bounds.start : 0;
  const windowLeft = maxOffset ? (offset / duration) * 100 : 0;
  const windowWidth = Math.min(100, (WINDOW_MS / duration) * 100);

  function startDrag(event) {
    if (!ready || !timelineRef.current) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      start: windowStart,
    };
  }

  function dragWindow(event) {
    const drag = dragRef.current;
    const width = timelineRef.current?.getBoundingClientRect().width;
    if (!drag || !width || drag.pointerId !== event.pointerId) return;
    const delta = ((event.clientX - drag.x) / width) * duration;
    const next = clamp(
      drag.start + delta,
      bounds.start,
      bounds.end - WINDOW_MS,
    );
    drag.latest = next;
    setWindowStart(next);
  }

  function finishDrag(event) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    queryWindow(drag.latest ?? drag.start);
  }

  function moveWindow(delta) {
    if (!ready || windowStart === null) return;
    const next = clamp(
      windowStart + delta,
      bounds.start,
      bounds.end - WINDOW_MS,
    );
    setWindowStart(next);
    queryWindow(next);
  }

  function handleWindowKeyDown(event) {
    const step = Math.max(1000, Number(session.segment_seconds || 30) * 1000);
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveWindow(-step);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      moveWindow(step);
    } else if (event.key === "Home" && bounds) {
      event.preventDefault();
      setWindowStart(bounds.start);
      queryWindow(bounds.start);
    } else if (event.key === "End" && bounds) {
      event.preventDefault();
      const latest = bounds.end - WINDOW_MS;
      setWindowStart(latest);
      queryWindow(latest);
    }
  }

  return (
    <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-6 shadow-xl">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="m-0 text-lg font-semibold text-white">5 分钟时间窗口回溯</h2>
          <p className="mt-1 text-sm text-slate-400">
            拖动时间轴上的窗口，松开后自动生成对应区间的火焰图
          </p>
        </div>
        <button
          type="button"
          disabled={!ready || windowStart === null || loading}
          onClick={() => queryWindow(windowStart)}
          className="rounded-lg border border-purple-400/40 bg-purple-500/15 px-4 py-2 text-sm text-purple-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "正在分析…" : "重新分析当前窗口"}
        </button>
      </div>

      {ready && windowStart !== null ? (
        <div className="rounded-xl border border-slate-700 bg-slate-950/55 p-4">
          <div className="mb-4 grid gap-3 text-sm md:grid-cols-[1fr_auto_1fr] md:items-center">
            <div>
              <span className="block text-xs text-slate-500">窗口开始</span>
              <strong className="font-mono text-cyan-300">
                {formatTimestamp(windowStart)}
              </strong>
            </div>
            <span className="rounded-full border border-purple-400/30 bg-purple-500/10 px-4 py-1 text-center text-xs font-semibold text-purple-200">
              固定 5 分钟
            </span>
            <div className="md:text-right">
              <span className="block text-xs text-slate-500">窗口结束</span>
              <strong className="font-mono text-cyan-300">
                {formatTimestamp(windowStart + WINDOW_MS)}
              </strong>
            </div>
          </div>

          <div
            ref={timelineRef}
            className="relative h-24 select-none rounded-lg border border-slate-700 bg-slate-900/90"
          >
            <div className="absolute inset-x-3 top-10 h-3 rounded-full bg-slate-800">
              {segments.map((segment) => {
                const start = new Date(segment.start_at).getTime();
                const end = new Date(segment.end_at).getTime();
                const left = ((start - bounds.start) / duration) * 100;
                const width = Math.max(
                  0.35,
                  ((end - start) / duration) * 100,
                );
                return (
                  <span
                    key={segment.id}
                    title={`${formatTimestamp(start)} – ${formatTimestamp(end)}`}
                    className="absolute inset-y-0 rounded-sm bg-cyan-500/55"
                    style={{ left: `${left}%`, width: `${width}%` }}
                  />
                );
              })}
            </div>

            <button
              type="button"
              aria-label="拖动五分钟分析窗口"
              aria-valuemin={bounds.start}
              aria-valuemax={bounds.end - WINDOW_MS}
              aria-valuenow={windowStart}
              onPointerDown={startDrag}
              onPointerMove={dragWindow}
              onPointerUp={finishDrag}
              onPointerCancel={finishDrag}
              onKeyDown={handleWindowKeyDown}
              className="absolute bottom-3 top-3 cursor-grab touch-none rounded-lg border-2 border-purple-300 bg-purple-500/20 shadow-[0_0_24px_rgba(168,85,247,0.28)] outline-none transition-[background-color,box-shadow] active:cursor-grabbing focus-visible:ring-2 focus-visible:ring-purple-300"
              style={{
                left: `calc(0.75rem + (100% - 1.5rem) * ${windowLeft / 100})`,
                width: `calc((100% - 1.5rem) * ${windowWidth / 100})`,
              }}
            >
            </button>
          </div>

          <div className="mt-2 flex justify-between text-xs font-mono text-slate-500">
            <span>{shortTime(bounds.start)}</span>
            <span>{shortTime(bounds.end)}</span>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-700 px-4 py-10 text-center text-sm text-slate-500">
          {bounds
            ? `持续采集满 5 分钟后可回溯，当前已采集 ${Math.max(0, Math.floor((bounds.end - bounds.start) / 1000))} 秒`
            : "正在建立持续采集时间轴"}
        </div>
      )}

      {message && <p className="mt-4 text-sm text-red-400">{message}</p>}
      {result && <div className="mt-6"><ProfileVisualization result={result} collector={session.collector} /></div>}
      <AttributionPanel
        attribution={attributions[0] || null}
        config={attributionConfig}
      />
    </section>
  );
}

export default function ContinuousView({
  agents,
  sessions,
  selectedSession,
  onCreated,
  onSelectSession,
  onStopSession,
}) {
  const currentSession =
    sessions.find((session) => session.id === selectedSession?.id) ||
    selectedSession;

  return (
    <>
      <ContinuousForm agents={agents} onCreated={onCreated} />
      <SessionTable sessions={sessions} onSelect={onSelectSession} onStop={onStopSession} />
      <WindowPanel session={currentSession} />
    </>
  );
}
