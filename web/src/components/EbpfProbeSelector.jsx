import React from "react";

import { EBPF_PROBES } from "../config/profiling.js";

export default function EbpfProbeSelector({ value, onChange, accent = "primary" }) {
  const toggle = (probe) => {
    if (value.includes(probe)) {
      if (value.length > 1) onChange(value.filter((item) => item !== probe));
    } else {
      onChange([...value, probe]);
    }
  };
  const selectedClass =
    accent === "accent"
      ? "border-accent/60 bg-accent/10"
      : "border-primary/60 bg-primary/10";

  return (
    <fieldset className="lg:col-span-3">
      <legend className="mb-2 text-sm font-medium text-slate-300">
        eBPF 内核探针（至少选择一个）
      </legend>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {EBPF_PROBES.map((probe) => (
          <label
            key={probe.value}
            className={`cursor-pointer rounded-lg border p-3 ${
              value.includes(probe.value)
                ? selectedClass
                : "border-slate-700 bg-slate-800/40"
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                className="mt-1"
                type="checkbox"
                checked={value.includes(probe.value)}
                onChange={() => toggle(probe.value)}
              />
              <span>
                <strong className="block text-sm text-white">{probe.label}</strong>
                <span className="mt-1 block text-xs font-mono text-slate-400">
                  {probe.technicalName}
                </span>
                <span className="mt-1 block text-xs text-slate-500">
                  {probe.description}
                </span>
              </span>
            </div>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
