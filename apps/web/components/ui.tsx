"use client";

export function RiskBadge({ risk }: { risk: string }) {
  const map: Record<string, string> = {
    high: "bg-rose-500/15 text-rose-300 border border-rose-500/30",
    medium: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
    low: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30",
  };
  return (
    <span className={`badge ${map[risk] ?? "bg-slate-700 text-slate-200"}`}>
      {risk.toUpperCase()}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    draft: "bg-slate-700/40 text-slate-300",
    profiled: "bg-sky-500/15 text-sky-300",
    generated: "bg-brand-500/15 text-brand-300",
    reviewed: "bg-violet-500/15 text-violet-300",
    approved: "bg-emerald-500/15 text-emerald-300",
    rejected: "bg-rose-500/15 text-rose-300",
    needs_review: "bg-amber-500/15 text-amber-300",
    exported: "bg-teal-500/15 text-teal-300",
  };
  return (
    <span className={`badge ${map[status] ?? "bg-slate-700 text-slate-200"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function ScoreRing({
  value,
  label,
}: {
  value: number;
  label: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    pct >= 85 ? "#34d399" : pct >= 65 ? "#fbbf24" : "#fb7185";
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="relative flex h-28 w-28 items-center justify-center rounded-full"
        style={{
          background: `conic-gradient(${color} ${pct * 3.6}deg, rgba(255,255,255,0.06) 0deg)`,
        }}
      >
        <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-slate-950">
          <span className="text-2xl font-bold">{value}</span>
          <span className="text-[10px] text-slate-500">/ 100</span>
        </div>
      </div>
      <span className="text-sm text-slate-400">{label}</span>
    </div>
  );
}

export function Metric({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}

export function CheckRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-800 py-2 last:border-0">
      <div className="flex items-center gap-2">
        <span
          className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
            ok ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"
          }`}
        >
          {ok ? "✓" : "!"}
        </span>
        <span className="text-sm text-slate-200">{label}</span>
      </div>
      <span className="text-xs text-slate-400">{detail}</span>
    </div>
  );
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Delete permanently",
  cancelLabel = "Cancel",
  loading = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      <button
        type="button"
        aria-label="Close dialog"
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
        onClick={onCancel}
        disabled={loading}
      />
      <div className="relative w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl shadow-black/40">
        <h2 id="confirm-modal-title" className="text-lg font-semibold text-slate-100">
          {title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">{message}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            className="btn-ghost"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className="btn bg-rose-600 text-white hover:bg-rose-500"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? "Deleting…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
