"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

const INDUSTRIES = [
  "healthcare",
  "finance",
  "insurance",
  "saas",
  "retail",
  "general",
];

const TEMPLATES: Record<string, { description: string }> = {
  healthcare: { description: "Patient appointments, claims, or lab results." },
  finance: { description: "Transactions, loan applications, or credit risk data." },
  insurance: { description: "Insurance claims and customer profiles." },
  saas: { description: "User events, subscriptions, support tickets." },
  retail: { description: "Orders, customers, inventory, returns." },
  general: { description: "" },
};

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("healthcare");
  const [description, setDescription] = useState(
    TEMPLATES.healthcare.description
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applyTemplate(ind: string) {
    setIndustry(ind);
    setDescription(TEMPLATES[ind]?.description ?? "");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const project = await api.createProject({
        name,
        industry,
        description,
      });
      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-bold">Create a project</h1>
      <p className="mb-6 text-sm text-slate-400">
        A project groups your source data, synthetic runs, and safety reports.
      </p>

      <form onSubmit={submit} className="card space-y-5">
        <div>
          <label className="label">Project name</label>
          <input
            className="input"
            placeholder="Synthetic Patient Appointments"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div>
          <label className="label">Industry</label>
          <div className="flex flex-wrap gap-2">
            {INDUSTRIES.map((ind) => (
              <button
                type="button"
                key={ind}
                onClick={() => applyTemplate(ind)}
                className={`badge px-3 py-1 capitalize ${
                  industry === ind
                    ? "bg-brand-600 text-white"
                    : "border border-slate-700 text-slate-300 hover:bg-slate-800"
                }`}
              >
                {ind}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label">Description</label>
          <textarea
            className="input min-h-[90px]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {error && <div className="text-sm text-rose-400">{error}</div>}

        <div className="flex justify-end gap-3">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => router.push("/")}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={submitting || !name}
          >
            {submitting ? "Creating…" : "Create project"}
          </button>
        </div>
      </form>
    </div>
  );
}
