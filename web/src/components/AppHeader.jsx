import React from "react";

import { ActivityIcon, ClockIcon } from "./Icons.jsx";

export default function AppHeader({ activeMode, onModeChange }) {
  const tabClass = (mode) =>
    `flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition ${
      activeMode === mode
        ? "bg-primary text-white shadow-lg shadow-primary/50"
        : "text-slate-300 hover:bg-slate-700/50 hover:text-white"
    }`;

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-700/50 bg-slate-900/80 shadow-lg backdrop-blur-md">
      <div className="mx-auto max-w-[1600px] px-6 py-4">
        <div className="flex flex-col items-center justify-between gap-4 lg:flex-row">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-gradient-to-br from-primary to-secondary p-2">
              <ActivityIcon />
            </div>
            <div>
              <h1 className="m-0 text-xl font-bold text-white">Mini-Drop</h1>
              <p className="m-0 text-sm text-slate-400">性能采集与分析平台</p>
            </div>
          </div>
          <div
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 p-1"
            role="tablist"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeMode === "task"}
              className={tabClass("task")}
              onClick={() => onModeChange("task")}
            >
              <ActivityIcon />
              创建 CPU 采样任务
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeMode === "continuous"}
              className={tabClass("continuous")}
              onClick={() => onModeChange("continuous")}
            >
              <ClockIcon />
              Continuous Profiling
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
