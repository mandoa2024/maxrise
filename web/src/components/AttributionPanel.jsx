import React from "react";

function evidenceLabel(item) {
  if (item.function) {
    return `${item.function}: ${item.baseline_self_percent}% → ${item.target_self_percent}% (${item.delta_pp > 0 ? "+" : ""}${item.delta_pp}pp)`;
  }
  if (item.frames) {
    return `${item.frames.join(" → ")}: ${item.baseline_percent}% → ${item.target_percent}%`;
  }
  if (item.metric) {
    return `${item.metric}: ${item.baseline} → ${item.target} (${item.ratio ?? "N/A"}x)`;
  }
  if (item.type === "metadata") {
    return `采集元数据：${item.collector} / PID ${item.pid}`;
  }
  return item.evidence_id || "证据";
}

function badgeClass(value) {
  if (value === "HIGH") return "border-red-500/40 bg-red-500/15 text-red-300";
  if (value === "MEDIUM") return "border-amber-500/40 bg-amber-500/15 text-amber-300";
  return "border-cyan-500/40 bg-cyan-500/15 text-cyan-300";
}

export default function AttributionPanel({
  attribution,
  config,
  onRun,
  running = false,
  showManual = false,
}) {
  if (!attribution) {
    return (
      <section className="mt-6 rounded-xl border border-purple-500/25 bg-purple-500/5 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="m-0 text-sm font-semibold text-purple-100">
              智能归因
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              自动监控中。达到异常阈值并具备 baseline 后会生成可验证报告。
              {config && !config.llm_configured
                ? " 当前未配置 API Key，将降级为确定性差分报告。"
                : ""}
            </p>
          </div>
          {showManual && onRun && (
            <button
              type="button"
              disabled={running}
              onClick={onRun}
              className="rounded-lg border border-purple-400/40 bg-purple-500/15 px-4 py-2 text-sm text-purple-200 disabled:opacity-50"
            >
              {running ? "正在归因…" : "立即归因"}
            </button>
          )}
        </div>
      </section>
    );
  }

  const report = attribution.report;
  return (
    <section className="mt-6 rounded-xl border border-purple-500/30 bg-slate-950/55 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="m-0 text-sm font-semibold text-purple-100">
            智能归因报告
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {attribution.trigger === "AUTO" ? "自动触发" : "手动触发"} ·{" "}
            {attribution.mode === "LLM"
              ? attribution.model
              : "确定性降级模式"}{" "}
            · {attribution.status}
          </p>
        </div>
        {report?.verification?.verified && (
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300">
            已验证 {report.verification.evidence_count} 条证据
          </span>
        )}
      </div>

      {attribution.status === "FAILED" && (
        <p className="mt-4 text-sm text-red-400">{attribution.error}</p>
      )}

      {report && (
        <>
          <p className="mt-4 text-sm leading-6 text-slate-200">
            {report.summary}
          </p>
          <div className="mt-4 space-y-4">
            {(report.findings || []).map((finding, index) => (
              <article
                key={`${finding.subject}-${index}`}
                className="rounded-lg border border-slate-700 bg-slate-900/70 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <strong className="text-sm text-white">
                    {finding.subject}
                  </strong>
                  <span className={`rounded border px-2 py-0.5 text-xs ${badgeClass(finding.impact)}`}>
                    影响 {finding.impact}
                  </span>
                  <span className={`rounded border px-2 py-0.5 text-xs ${badgeClass(finding.confidence)}`}>
                    置信度 {finding.confidence}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-300">{finding.claim}</p>
                <div className="mt-3 space-y-2">
                  {(finding.evidence || []).map((item) => (
                    <div
                      key={item.evidence_id}
                      className="rounded border border-cyan-800/50 bg-cyan-950/30 px-3 py-2 text-xs font-mono text-cyan-200"
                    >
                      {evidenceLabel(item)}
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-slate-400">
                  建议：{finding.recommendation}
                </p>
              </article>
            ))}
          </div>
          {!!report.limitations?.length && (
            <div className="mt-4 rounded-lg border border-amber-700/40 bg-amber-950/20 p-3 text-xs text-amber-200">
              限制：{report.limitations.join("；")}
            </div>
          )}
        </>
      )}
    </section>
  );
}
