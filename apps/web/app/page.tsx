"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Project } from "@/lib/api";
import { ConfirmModal, StatusBadge } from "@/components/ui";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message));
  }, []);

  function openDeleteDialog(e: React.MouseEvent, p: Project) {
    e.preventDefault();
    e.stopPropagation();
    setPendingDelete(p);
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteProject(pendingDelete.id);
      setProjects((prev) =>
        prev ? prev.filter((x) => x.id !== pendingDelete.id) : prev
      );
      setPendingDelete(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="card relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight">
            Generate useful fake data.
          </h1>
          <p className="mt-2 text-slate-400">
            Keep the patterns, remove the people, and document the risk.
            Upload a CSV, synthesize a privacy-safe copy, then produce an
            evidence-based safety &amp; utility report.
          </p>
          <div className="mt-5 flex gap-3">
            <Link href="/projects/new" className="btn-primary">
              Create a project
            </Link>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Projects</h2>
          {projects && (
            <span className="text-sm text-slate-500">
              {projects.length} total
            </span>
          )}
        </div>

        {error && (
          <div className="card border-rose-500/40 text-rose-300">
            Could not reach the API: {error}. Is the backend running on port
            8000?
          </div>
        )}

        {!projects && !error && (
          <div className="card text-slate-400">Loading projects…</div>
        )}

        {projects && projects.length === 0 && (
          <div className="card text-center text-slate-400">
            No projects yet.{" "}
            <Link href="/projects/new" className="text-brand-400 underline">
              Create your first one
            </Link>
            .
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects?.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              className="card relative transition hover:border-brand-500/50 hover:bg-slate-900"
            >
              <button
                type="button"
                aria-label={`Delete ${p.name}`}
                title="Delete project"
                onClick={(e) => openDeleteDialog(e, p)}
                className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition hover:bg-rose-500/15 hover:text-rose-300"
              >
                ✕
              </button>
              <div className="flex items-start justify-between pr-8">
                <h3 className="font-semibold">{p.name}</h3>
                <StatusBadge status={p.status} />
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-slate-400">
                {p.description || "No description"}
              </p>
              <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                <span className="rounded bg-slate-800 px-2 py-0.5">
                  {p.industry}
                </span>
                {p.use_case && (
                  <span className="truncate">{p.use_case}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      </section>

      <ConfirmModal
        open={!!pendingDelete}
        title="Delete project permanently?"
        message={
          pendingDelete
            ? `Are you sure you want to delete "${pendingDelete.name}" permanently? This cannot be undone.`
            : ""
        }
        confirmLabel="Delete permanently"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => {
          if (!deleting) setPendingDelete(null);
        }}
      />
    </div>
  );
}
