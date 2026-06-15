"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  api,
  Dataset,
  Preview,
  Project,
  Run,
  SafetyReport,
} from "@/lib/api";
import {
  CheckRow,
  Metric,
  RiskBadge,
  ScoreRing,
  StatusBadge,
} from "@/components/ui";

function SectionHeader({
  step,
  title,
  done,
}: {
  step: number;
  title: string;
  done?: boolean;
}) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span
        className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold ${
          done ? "bg-emerald-500/20 text-emerald-300" : "bg-brand-600 text-white"
        }`}
      >
        {done ? "✓" : step}
      </span>
      <h2 className="text-lg font-semibold">{title}</h2>
    </div>
  );
}

export default function ProjectWorkspace({
  params,
}: {
  params: { id: string };
}) {
  const projectId = Number(params.id);
  const [project, setProject] = useState<Project | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [report, setReport] = useState<SafetyReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [reporting, setReporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [rowCount, setRowCount] = useState(1000);
  const [preserveCorr, setPreserveCorr] = useState(true);
  const [addNoise, setAddNoise] = useState(true);

  useEffect(() => {
    api.getProject(projectId).then(setProject).catch((e) => setError(e.message));
    api.listDatasets(projectId).then((d) => {
      if (d.length) setDataset(d[0]);
    });
  }, [projectId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setRun(null);
    setPreview(null);
    setReport(null);
    try {
      const ds = await api.uploadDataset(projectId, file);
      setDataset(ds);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleGenerate() {
    if (!dataset) return;
    setGenerating(true);
    setError(null);
    setReport(null);
    try {
      const r = await api.generate(dataset.id, {
        row_count: rowCount,
        preserve_correlations: preserveCorr,
        add_noise: addNoise,
      });
      setRun(r);
      const p = await api.preview(r.id);
      setPreview(p);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleReport() {
    if (!run) return;
    setReporting(true);
    setError(null);
    try {
      const rep = await api.buildReport(run.id);
      setReport(rep);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setReporting(false);
    }
  }

  async function approve(status: string) {
    if (!run) return;
    const rep = await api.setApproval(run.id, status);
    setReport(rep);
  }

  const profile = dataset?.profile_json;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-slate-500 hover:text-slate-300">
            ← All projects
          </Link>
          <h1 className="mt-1 text-2xl font-bold">{project?.name ?? "…"}</h1>
          <p className="text-sm text-slate-400">
            {project?.industry} · {project?.use_case || "No use case set"}
          </p>
        </div>
        {project && <StatusBadge status={project.status} />}
      </div>

      {error && (
        <div className="card border-rose-500/40 text-rose-300">{error}</div>
      )}

      {/* STEP 1: Upload + profile */}
      <section className="card">
        <SectionHeader step={1} title="Source data & profiling" done={!!dataset} />
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.pdf"
            onChange={handleUpload}
            className="hidden"
          />
          <button
            className="btn-primary"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading
              ? "Profiling…"
              : dataset
              ? "Replace file"
              : "Upload CSV / PDF"}
          </button>
          {dataset && (
            <span className="text-sm text-slate-400">
              {dataset.filename} · {dataset.row_count.toLocaleString()} rows ·{" "}
              {dataset.column_count} columns
            </span>
          )}
        </div>

        {profile && (
          <div className="mt-5">
            <div className="mb-3 flex gap-3 text-sm">
              <span className="rounded-lg bg-rose-500/10 px-3 py-1 text-rose-300">
                {profile.risk_summary.high} high-risk
              </span>
              <span className="rounded-lg bg-amber-500/10 px-3 py-1 text-amber-300">
                {profile.risk_summary.medium} medium
              </span>
              <span className="rounded-lg bg-emerald-500/10 px-3 py-1 text-emerald-300">
                {profile.risk_summary.low} low
              </span>
            </div>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-900/80 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-2">Column</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Detected</th>
                    <th className="px-4 py-2">Missing</th>
                    <th className="px-4 py-2">Unique</th>
                    <th className="px-4 py-2">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.columns.map((c) => (
                    <tr key={c.name} className="border-t border-slate-800">
                      <td className="px-4 py-2 font-medium">{c.name}</td>
                      <td className="px-4 py-2 text-slate-400">
                        {c.logical_type}
                      </td>
                      <td className="px-4 py-2 text-slate-400">
                        {c.pii_kind ?? "—"}
                      </td>
                      <td className="px-4 py-2 text-slate-400">
                        {(c.missing_pct * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2 text-slate-400">
                        {c.unique_count}
                      </td>
                      <td className="px-4 py-2">
                        <RiskBadge risk={c.risk} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* STEP 2: Generate */}
      {dataset && (
        <section className="card">
          <SectionHeader step={2} title="Generate synthetic data" done={!!run} />
          <div className="grid gap-5 sm:grid-cols-3">
            <div>
              <label className="label">Rows to generate</label>
              <input
                type="number"
                className="input"
                min={1}
                max={1000000}
                value={rowCount}
                onChange={(e) => setRowCount(Number(e.target.value))}
              />
            </div>
            <label className="flex items-center gap-3 sm:mt-7">
              <input
                type="checkbox"
                checked={preserveCorr}
                onChange={(e) => setPreserveCorr(e.target.checked)}
                className="h-4 w-4 accent-brand-500"
              />
              <span className="text-sm text-slate-300">
                Preserve correlations
              </span>
            </label>
            <label className="flex items-center gap-3 sm:mt-7">
              <input
                type="checkbox"
                checked={addNoise}
                onChange={(e) => setAddNoise(e.target.checked)}
                className="h-4 w-4 accent-brand-500"
              />
              <span className="text-sm text-slate-300">
                Add privacy noise
              </span>
            </label>
          </div>
          <div className="mt-5 flex gap-3">
            <button
              className="btn-primary"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? "Generating…" : "Generate"}
            </button>
            <button
              className="btn-ghost"
              onClick={handleGenerate}
              disabled={generating || !run}
              title="Generate a fresh synthetic dataset with new random values"
            >
              {generating ? "Working…" : "Regenerate data"}
            </button>
          </div>

          {preview && (
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-300">
                  Preview (first {preview.rows.length} rows)
                </h3>
                {run && (
                  <div className="flex gap-2">
                    <a
                      className="btn-ghost"
                      href={api.downloadUrl(run.id, "csv")}
                    >
                      Download CSV
                    </a>
                    <a
                      className="btn-ghost"
                      href={api.downloadUrl(run.id, "pdf")}
                    >
                      Download PDF
                    </a>
                  </div>
                )}
              </div>
              <div className="max-h-80 overflow-auto rounded-xl border border-slate-800">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-900/95 text-left text-slate-500">
                    <tr>
                      {preview.columns.map((c) => (
                        <th key={c} className="whitespace-nowrap px-3 py-2">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i} className="border-t border-slate-800/70">
                        {preview.columns.map((c) => (
                          <td
                            key={c}
                            className="whitespace-nowrap px-3 py-1.5 text-slate-300"
                          >
                            {row[c] === null ? (
                              <span className="text-slate-600">∅</span>
                            ) : (
                              String(row[c])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      {/* STEP 3: Safety report */}
      {run && (
        <section className="card">
          <SectionHeader step={3} title="Privacy & utility safety report" done={!!report} />
          {!report && (
            <button
              className="btn-primary"
              onClick={handleReport}
              disabled={reporting}
            >
              {reporting ? "Scoring…" : "Run safety scan & build report"}
            </button>
          )}

          {report && (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center gap-8">
                <ScoreRing value={report.privacy_score} label="Privacy" />
                <ScoreRing value={report.utility_score} label="Trend Accuracy" />
                <div>
                  <div className="text-sm text-slate-400">Risk level</div>
                  <div className="mt-1">
                    <RiskBadge risk={report.risk_level} />
                  </div>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-800 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-slate-200">
                    Privacy checks
                  </h3>
                  <CheckRow
                    label="PII removed"
                    ok={report.metrics_json.privacy.checks.pii_removed}
                    detail={`leak ${(report.metrics_json.privacy.pii_leak_rate * 100).toFixed(1)}%`}
                  />
                  <CheckRow
                    label="No duplicated real rows"
                    ok={report.metrics_json.privacy.checks.no_duplicate_rows}
                    detail={`${report.metrics_json.privacy.duplicate_rows} rows`}
                  />
                  <CheckRow
                    label="Low similarity to real rows"
                    ok={report.metrics_json.privacy.checks.low_similarity}
                    detail={`${(report.metrics_json.privacy.too_similar_rate * 100).toFixed(1)}% near`}
                  />
                </div>

                <div className="rounded-xl border border-slate-800 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-slate-200">
                    Trend accuracy breakdown
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    <Metric
                      label="Distribution"
                      value={`${(report.metrics_json.utility.distribution_similarity * 100).toFixed(0)}%`}
                    />
                    <Metric
                      label="Correlation"
                      value={
                        report.metrics_json.utility.correlation_similarity == null
                          ? "n/a"
                          : `${(report.metrics_json.utility.correlation_similarity * 100).toFixed(0)}%`
                      }
                    />
                    <Metric
                      label="Missing match"
                      value={`${(report.metrics_json.utility.missing_value_match * 100).toFixed(0)}%`}
                    />
                  </div>
                </div>
              </div>

              {/* Approval workflow */}
              <div className="rounded-xl border border-slate-800 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-slate-400">
                      Approval status:
                    </span>
                    <StatusBadge status={report.approved_status} />
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="btn-ghost"
                      onClick={() => approve("rejected")}
                    >
                      Reject
                    </button>
                    <button
                      className="btn-primary"
                      onClick={() => approve("approved")}
                    >
                      Approve
                    </button>
                    <a
                      className="btn-ghost"
                      href={api.reportDownloadUrl(run.id)}
                    >
                      Download report (.md)
                    </a>
                  </div>
                </div>
              </div>

            </div>
          )}
        </section>
      )}
    </div>
  );
}
