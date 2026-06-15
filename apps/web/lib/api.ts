export type Project = {
  id: number;
  name: string;
  description: string;
  industry: string;
  use_case: string;
  status: string;
  created_at: string;
};

export type ColumnProfile = {
  name: string;
  logical_type: string;
  pandas_dtype: string;
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  unique_ratio: number;
  pii_kind: string | null;
  risk: "high" | "medium" | "low";
  sample_values: string[];
  stats?: Record<string, any>;
};

export type DatasetProfile = {
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
  risk_summary: { high: number; medium: number; low: number };
  sensitive_fields: string[];
};

export type Dataset = {
  id: number;
  project_id: number;
  filename: string;
  row_count: number;
  column_count: number;
  profile_json: DatasetProfile;
  created_at: string;
};

export type Run = {
  id: number;
  project_id: number;
  dataset_id: number | null;
  mode: string;
  generator_type: string;
  status: string;
  row_count: number;
  settings_json: Record<string, any>;
  created_at: string;
};

export type Preview = { columns: string[]; rows: Record<string, any>[] };

export type SafetyReport = {
  id: number;
  synthetic_run_id: number;
  privacy_score: number;
  utility_score: number;
  risk_level: "low" | "medium" | "high";
  metrics_json: any;
  report_text: string;
  generated_by: string;
  approved_status: string;
  created_at: string;
};

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listProjects: () => fetch("/api/projects").then((r) => jsonOrThrow<Project[]>(r)),
  getProject: (id: number) =>
    fetch(`/api/projects/${id}`).then((r) => jsonOrThrow<Project>(r)),
  createProject: (data: Partial<Project>) =>
    fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => jsonOrThrow<Project>(r)),
  deleteProject: (id: number) =>
    fetch(`/api/projects/${id}`, { method: "DELETE" }).then((r) =>
      jsonOrThrow<{ deleted: boolean }>(r)
    ),
  listProjectRuns: (id: number) =>
    fetch(`/api/projects/${id}/runs`).then((r) => jsonOrThrow<Run[]>(r)),

  listDatasets: (projectId: number) =>
    fetch(`/api/projects/${projectId}/datasets`).then((r) =>
      jsonOrThrow<Dataset[]>(r)
    ),
  uploadDataset: (projectId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`/api/projects/${projectId}/datasets`, {
      method: "POST",
      body: fd,
    }).then((r) => jsonOrThrow<Dataset>(r));
  },

  generate: (
    datasetId: number,
    body: {
      row_count: number;
      preserve_correlations: boolean;
      add_noise: boolean;
      seed?: number | null;
    }
  ) =>
    fetch(`/api/datasets/${datasetId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => jsonOrThrow<Run>(r)),

  preview: (runId: number) =>
    fetch(`/api/runs/${runId}/preview`).then((r) => jsonOrThrow<Preview>(r)),

  buildReport: (runId: number) =>
    fetch(`/api/runs/${runId}/report`, { method: "POST" }).then((r) =>
      jsonOrThrow<SafetyReport>(r)
    ),
  getReport: (runId: number) =>
    fetch(`/api/runs/${runId}/report`).then((r) => jsonOrThrow<SafetyReport>(r)),
  setApproval: (runId: number, status: string) =>
    fetch(`/api/runs/${runId}/approval`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved_status: status }),
    }).then((r) => jsonOrThrow<SafetyReport>(r)),

  downloadUrl: (runId: number, format: "csv" | "pdf" = "csv") =>
    `/api/runs/${runId}/download?format=${format}`,
  reportDownloadUrl: (runId: number) => `/api/runs/${runId}/report/download`,
};
