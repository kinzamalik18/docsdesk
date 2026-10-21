export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type Citation = {
  number: number;
  doc_id: string;
  doc_title: string;
  section: string;
  snippet: string;
};

export type ChatResponse = {
  answer: string;
  answered: boolean;
  citations: Citation[];
  top_similarity: number;
};

export type Info = {
  company: string;
  provider: string;
  chat_model: string;
  persistent_store: boolean;
  chunks: number;
  public_dashboard: boolean;
};

export type SourceDoc = { doc_id: string; title: string; chunks: number };

export type Gap = { question: string; top_similarity: number; reason: string; created_at: string };

export type EvalRow = {
  id: string;
  question: string;
  answerable: boolean;
  answered: boolean;
  answer: string;
  cited_docs: string[];
  top_similarity: number;
  retrieval_hit?: boolean;
  citation_hit?: boolean;
  fact_match?: boolean;
  passed: boolean;
};

export type EvalReport = {
  created_at: string;
  duration_seconds: number;
  provider: string;
  chat_model: string;
  embed_model: string;
  top_k: number;
  min_similarity: number;
  summary: {
    total: number;
    passed: number;
    answerable: number;
    unanswerable: number;
    answer_rate: number | null;
    retrieval_hit_rate: number | null;
    citation_accuracy: number | null;
    fact_match_rate: number | null;
    correct_refusal_rate: number | null;
  };
  rows: EvalRow[];
};

export type EvalState = {
  status: { state: "idle" | "running" | "done" | "failed"; done: number; total: number; error: string };
  report: EvalReport | null;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit & { adminToken?: string }): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (init?.adminToken) headers.set("X-Admin-Token", init.adminToken);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Can't reach the DocsDesk server. Check your connection and try again.", 0);
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(detail, response.status);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

// Free hosting sleeps when idle, so the first request after a while can take up to a minute.
export const SLOW_REQUEST_MS = 6000;
