import React from "react";

const COLORS = {
  ONLINE: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
  DONE: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
  OFFLINE: "bg-red-500/20 text-red-400 border-red-500/50",
  FAILED: "bg-red-500/20 text-red-400 border-red-500/50",
  RUNNING: "bg-blue-500/20 text-blue-400 border-blue-500/50",
  UPLOADING: "bg-blue-500/20 text-blue-400 border-blue-500/50",
  PENDING: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
  RECOVERED: "bg-amber-500/20 text-amber-400 border-amber-500/50",
};

export default function StatusBadge({ value }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${
        COLORS[value] ||
        "bg-slate-500/20 text-slate-400 border-slate-500/50"
      }`}
    >
      {value}
    </span>
  );
}
