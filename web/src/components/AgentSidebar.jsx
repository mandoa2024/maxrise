import React, { useEffect } from "react";

import { formatTimestamp } from "../lib/format.js";
import { CloseIcon, ServerIcon } from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

export default function AgentSidebar({ open, agents, audits, onClose }) {
  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  return (
    <>
      <button
        type="button"
        aria-label="关闭 Agent 面板"
        className={`fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-[2px] transition ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />
      <aside
        aria-hidden={!open}
        className={`fixed bottom-4 left-4 top-[9rem] z-40 flex w-[calc(100vw-2rem)] max-w-md flex-col overflow-hidden rounded-2xl border border-slate-600/70 bg-slate-900/95 shadow-2xl transition lg:top-24 ${
          open
            ? "translate-x-0 opacity-100"
            : "pointer-events-none -translate-x-[110%] opacity-0"
        }`}
      >
        <header className="flex items-center justify-between border-b border-slate-700 px-5 py-4">
          <div>
            <h2 className="m-0 text-base font-semibold text-white">Agent 面板</h2>
            <p className="m-0 mt-1 text-xs text-slate-400">
              节点状态与最近审计事件
            </p>
          </div>
          <button
            type="button"
            aria-label="关闭 Agent 面板"
            onClick={onClose}
            className="cursor-pointer rounded-lg border border-slate-700 p-2 text-slate-400 hover:text-white"
          >
            <CloseIcon />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
            <ServerIcon /> Agent 状态
          </h3>
          <div className="space-y-3">
            {agents.length ? (
              agents.map((agent) => (
                <article
                  key={agent.id}
                  className="rounded-xl border border-slate-700/70 bg-slate-800/55 p-4"
                >
                  <div className="mb-2 flex justify-between gap-3">
                    <strong className="text-sm text-white">{agent.name}</strong>
                    <StatusBadge value={agent.status} />
                  </div>
                  <p className="m-0 text-xs font-mono text-slate-400">
                    {agent.hostname}
                  </p>
                  <p className="m-0 mt-1 text-xs text-slate-500">
                    {formatTimestamp(agent.last_heartbeat_at)}
                  </p>
                </article>
              ))
            ) : (
              <p className="py-6 text-center text-sm text-slate-500">
                等待 Agent 注册...
              </p>
            )}
          </div>
          <h3 className="mb-4 mt-7 text-sm font-semibold text-white">审计日志</h3>
          <div className="space-y-3">
            {audits.slice(0, 20).map((audit) => (
              <article
                key={`${audit.agent_id}-${audit.created_at}-${audit.event}`}
                className="rounded-xl border border-slate-700/60 bg-slate-800/35 p-3"
              >
                <div className="flex justify-between gap-3">
                  <span className="truncate text-xs font-mono text-slate-300">
                    {audit.agent_id}
                  </span>
                  <StatusBadge value={audit.event} />
                </div>
                <p className="m-0 mt-2 text-xs text-slate-400">{audit.reason}</p>
                <p className="m-0 mt-1 text-xs text-slate-600">
                  {formatTimestamp(audit.created_at)}
                </p>
              </article>
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}
