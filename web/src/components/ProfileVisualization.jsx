import React from "react";

import { EBPF_PROBES } from "../config/profiling.js";
import { formatKb } from "../lib/format.js";

function leafStacks(root) {
  const output = [];
  const walk = (node, path = []) => {
    const next = node.name === "root" ? path : [...path, node.name];
    if (!node.children?.length && next.length) {
      output.push({ frames: next, samples: node.value });
    }
    (node.children || []).forEach((child) => walk(child, next));
  };
  if (root) walk(root);
  return output.sort((a, b) => b.samples - a.samples);
}

function TopList({ title, items = [], unit = "samples", color = "orange" }) {
  const colorClass =
    color === "cyan"
      ? "text-cyan-300"
      : color === "amber"
        ? "text-amber-300"
        : "text-orange-400";
  return (
    <section>
      <h3 className="mb-3 mt-6 text-sm font-semibold text-white">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <tbody>
            {items.map((item) => (
              <tr key={item.name} className="border-b border-slate-700/50">
                <td className={`px-4 py-3 text-sm font-mono ${colorClass}`}>
                  {item.name}
                </td>
                <td className="px-4 py-3 text-right text-sm text-slate-400">
                  {item.samples} {unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Flamegraph({ result }) {
  if (result.flamegraph_svg) {
    const svg = result.flamegraph_svg.replace(
      /<svg\b([^>]*)>/,
      '<svg$1 width="100%" height="auto" preserveAspectRatio="xMinYMin meet">',
    );
    const srcDoc = `<!doctype html><style>html,body{margin:0;overflow:hidden}svg{display:block;width:100%;height:auto}</style>${svg}`;
    return (
      <iframe
        title="CPU FlameGraph"
        sandbox="allow-scripts"
        srcDoc={srcDoc}
        className="block h-[760px] w-full rounded-lg border border-slate-700 bg-white"
      />
    );
  }
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
      {leafStacks(result.flamegraph).map((stack) => (
        <div
          key={stack.frames.join(";")}
          className="my-1 truncate rounded bg-gradient-to-r from-orange-400 to-orange-600 p-2 text-xs text-orange-950"
        >
          {stack.frames.join(" → ")} ({stack.samples})
        </div>
      ))}
    </div>
  );
}

function Metrics({ metrics = {} }) {
  const cpu = metrics.cpu || metrics;
  const memory = metrics.memory || {};
  const items = [
    ["Collector", cpu.collector],
    ["Event", cpu.event],
    ["Duration", cpu.duration_seconds && `${cpu.duration_seconds}s`],
    ...(cpu.sampled_duration_seconds !== undefined
      ? [
          ["Sampled", `${cpu.sampled_duration_seconds}s`],
          ["Coverage", `${cpu.coverage_percent}%`],
        ]
      : []),
    ["Sample Rate", cpu.sample_rate_hz && `${cpu.sample_rate_hz} Hz`],
    ["Memory RSS", formatKb(memory.rss_kb)],
    ["Peak RSS", formatKb(memory.peak_rss_kb)],
  ];
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
      {items.map(([label, value]) => (
        <div
          key={label}
          className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-4"
        >
          <span className="block text-xs text-slate-400">{label}</span>
          <strong className="mt-2 block font-mono text-white">
            {value || "N/A"}
          </strong>
        </div>
      ))}
    </div>
  );
}

function KernelGroup({ source, result, description, unit }) {
  const stacks = leafStacks(result?.flamegraph);
  const max = Math.max(1, ...stacks.map((item) => item.samples));
  return (
    <section className="rounded-xl border border-cyan-500/30 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="m-0 text-sm font-semibold text-white">{description}</h4>
        <span className="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3 py-1 text-xs font-mono text-cyan-300">
          {source}
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {stacks.length ? (
          stacks.map((stack) => (
            <div
              key={stack.frames.join(";")}
              className="relative overflow-hidden rounded-lg border border-slate-700 bg-slate-900/80 p-3"
            >
              <div
                className="absolute inset-y-0 left-0 bg-cyan-500/15"
                style={{ width: `${(stack.samples / max) * 100}%` }}
              />
              <div className="relative flex flex-wrap items-center gap-2">
                {stack.frames
                  .filter((frame) => !["ebpf", "kernel", source].includes(frame))
                  .map((frame, index) => (
                    <React.Fragment key={`${frame}-${index}`}>
                      {index > 0 && <span className="text-slate-600">→</span>}
                      <span className="rounded border border-cyan-800/70 bg-cyan-950/60 px-2 py-1 text-xs font-mono text-cyan-100">
                        {frame}
                      </span>
                    </React.Fragment>
                  ))}
                <strong className="ml-auto text-xs font-mono text-cyan-300">
                  {stack.samples} {unit}
                </strong>
              </div>
            </div>
          ))
        ) : (
          <p className="py-6 text-center text-sm text-slate-500">
            该探针暂无命中数据
          </p>
        )}
      </div>
    </section>
  );
}

function EbpfView({ result }) {
  const sources = result.ebpf_sources || {};
  const details = Object.fromEntries(
    EBPF_PROBES.map((probe) => [probe.technicalName, probe]),
  );
  const selected =
    result.metrics?.cpu?.ebpf_probes ||
    result.metrics?.ebpf_probes ||
    Object.keys(sources)
      .filter((key) => key.startsWith("kprobe:"))
      .map((key) => key.slice(7));
  const groups = selected.map((probe) => `kprobe:${probe}`);
  if (sources["profile:hz"]) groups.push("profile:hz");

  return (
    <>
      <h3 className="mb-3 mt-6 text-sm font-semibold text-white">
        eBPF 内核采集结果
      </h3>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {groups.map((source) => (
          <KernelGroup
            key={source}
            source={source}
            result={sources[source]}
            description={
              source === "profile:hz"
                ? "周期内核采样"
                : details[source]?.label || "内核探针事件"
            }
            unit={source === "profile:hz" ? "samples" : "events"}
          />
        ))}
      </div>
    </>
  );
}

function PythonNode({ node, depth = 0, total = 1 }) {
  if (["py-spy", "python"].includes(node.name)) {
    return (node.children || []).map((child) => (
      <PythonNode key={child.name} node={child} depth={depth} total={total} />
    ));
  }
  return (
    <div className="mt-2" style={{ marginLeft: `${Math.min(depth, 8) * 20}px` }}>
      <div className="relative overflow-hidden rounded-lg border border-amber-500/25 bg-slate-900/80 px-3 py-2">
        <div
          className="absolute inset-y-0 left-0 bg-amber-500/15"
          style={{ width: `${Math.max(2, (node.value / total) * 100)}%` }}
        />
        <div className="relative flex justify-between gap-3">
          <span className="font-mono text-sm text-amber-100">{node.name}</span>
          <span className="text-xs font-mono text-amber-300">
            {node.value} samples
          </span>
        </div>
      </div>
      {(node.children || []).map((child) => (
        <PythonNode
          key={child.name}
          node={child}
          depth={depth + 1}
          total={total}
        />
      ))}
    </div>
  );
}

export default function ProfileVisualization({ result, collector }) {
  const actualCollector =
    result.metrics?.cpu?.collector ||
    result.metrics?.collector ||
    result.session?.collector ||
    collector;

  return (
    <>
      <h3 className="mb-3 text-sm font-semibold text-white">性能指标</h3>
      <Metrics metrics={result.metrics} />
      {actualCollector === "ebpf" ? (
        <EbpfView result={result} />
      ) : actualCollector === "py-spy" ? (
        <>
          <h3 className="mb-3 mt-6 text-sm font-semibold text-white">
            Python 调用树
          </h3>
          <div className="rounded-xl border border-amber-500/30 bg-slate-950/60 p-4">
            {(result.flamegraph?.children || []).map((child) => (
              <PythonNode
                key={child.name}
                node={child}
                total={result.flamegraph.value}
              />
            ))}
          </div>
          <TopList
            title="Top Python Functions"
            items={result.top_functions}
            color="amber"
          />
        </>
      ) : (
        <>
          <h3 className="mb-3 mt-6 text-sm font-semibold text-white">
            CPU 火焰图
          </h3>
          <Flamegraph result={result} />
          <TopList title="Top 函数" items={result.top_functions} />
        </>
      )}
    </>
  );
}
