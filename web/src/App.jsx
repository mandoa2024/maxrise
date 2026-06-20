import React, { useCallback, useEffect, useMemo, useState } from "react";

import AgentSidebar from "./components/AgentSidebar.jsx";
import AppHeader from "./components/AppHeader.jsx";
import { ServerIcon } from "./components/Icons.jsx";
import ContinuousView from "./features/continuous/ContinuousView.jsx";
import TaskView from "./features/tasks/TaskView.jsx";
import { api } from "./lib/api.js";

export default function App() {
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [audits, setAudits] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [pinnedTaskId, setPinnedTaskId] = useState(null);
  const [activeMode, setActiveMode] = useState("task");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [error, setError] = useState("");

  const loadTask = useCallback(async (taskId) => {
    setSelectedTask(await api(`/api/v1/tasks/${taskId}`));
  }, []);

  const load = useCallback(async () => {
    try {
      const [nextAgents, nextTasks, nextAudits, nextSessions] =
        await Promise.all([
          api("/api/v1/agents"),
          api("/api/v1/tasks"),
          api("/api/v1/agents/audit-logs"),
          api("/api/v1/profile-sessions"),
        ]);
      setAgents(nextAgents);
      setTasks(nextTasks);
      setAudits(nextAudits);
      setSessions(nextSessions);
      setError("");

      const pinned = pinnedTaskId
        ? nextTasks.find((task) => task.id === pinnedTaskId)
        : null;
      const candidate =
        pinned?.status === "DONE"
          ? pinned
          : nextTasks.find((task) => task.status === "DONE");
      if (candidate) await loadTask(candidate.id);
    } catch (loadError) {
      setError(loadError.message);
    }
  }, [loadTask, pinnedTaskId]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 3000);
    return () => window.clearInterval(timer);
  }, [load]);

  const selectTask = useCallback(
    async (taskId) => {
      setPinnedTaskId(taskId);
      await loadTask(taskId);
    },
    [loadTask],
  );

  const stopSession = useCallback(
    async (sessionId) => {
      await api(`/api/v1/profile-sessions/${sessionId}/stop`, {
        method: "POST",
      });
      await load();
    },
    [load],
  );

  const visibleTask = useMemo(
    () =>
      selectedTask && tasks.some((task) => task.id === selectedTask.id)
        ? selectedTask
        : null,
    [selectedTask, tasks],
  );

  return (
    <>
      <AppHeader activeMode={activeMode} onModeChange={setActiveMode} />
      <AgentSidebar
        open={sidebarOpen}
        agents={agents}
        audits={audits}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="mx-auto max-w-[1600px] space-y-6 px-6 py-6">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-600/70 bg-slate-800/70 px-4 py-2 text-sm font-medium text-slate-200"
        >
          <ServerIcon />
          Agent 面板
          <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs">
            {agents.length}
          </span>
        </button>

        {activeMode === "task" ? (
          <TaskView
            agents={agents}
            tasks={tasks}
            selectedTask={visibleTask}
            onCreated={load}
            onSelectTask={selectTask}
          />
        ) : (
          <ContinuousView
            agents={agents}
            sessions={sessions}
            selectedSession={selectedSession}
            onCreated={load}
            onSelectSession={setSelectedSession}
            onStopSession={stopSession}
          />
        )}

        {error && (
          <div className="rounded-lg border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-400">
            {error}
          </div>
        )}
      </main>
    </>
  );
}
