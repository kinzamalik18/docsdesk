"use client";

import { useCallback, useEffect, useState } from "react";

import { stripMarkdown } from "@/components/answer-text";
import { TokenField } from "@/components/token-field";
import { useAdminToken } from "@/lib/admin-token";
import { api, ApiError, type EvalReport, type EvalRow, type EvalState } from "@/lib/api";

const METRICS: { key: keyof EvalReport["summary"]; label: string; explain: string }[] = [
  {
    key: "citation_accuracy",
    label: "Cited the right article",
    explain: "Answerable questions where the answer cited the article that actually covers it.",
  },
  {
    key: "fact_match_rate",
    label: "Included the key fact",
    explain: "Answerable questions where the answer contained the expected detail, such as a price or a time limit.",
  },
  {
    key: "correct_refusal_rate",
    label: "Declined when it should",
    explain: "Questions the docs don't cover, where DocsDesk said so instead of guessing.",
  },
  {
    key: "retrieval_hit_rate",
    label: "Found the right article",
    explain: "Answerable questions where search returned the correct article among its top results.",
  },
  {
    key: "answer_rate",
    label: "Answered at all",
    explain: "Answerable questions that got an answer instead of a fallback.",
  },
];

function pct(value: number | null) {
  return value === null ? "n/a" : `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

function Mark({ ok }: { ok: boolean | undefined }) {
  if (ok === undefined) return <span className="text-ink-soft">n/a</span>;
  return ok ? <span className="font-semibold text-fern">Yes</span> : <span className="font-semibold text-margin">No</span>;
}

function RowDetail({ row }: { row: EvalRow }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className="border-b border-rule align-top">
        <td className="py-2.5 pr-3">
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="text-left hover:underline hover:underline-offset-4"
          >
            {row.question}
          </button>
          <span className="block text-sm text-ink-soft">{row.answerable ? "In the docs" : "Not in the docs"}</span>
        </td>
        <td className="py-2.5 pr-3 text-center">
          {row.answerable ? <Mark ok={row.citation_hit} /> : <span className="text-ink-soft">n/a</span>}
        </td>
        <td className="py-2.5 pr-3 text-center">
          {row.answerable ? <Mark ok={row.fact_match} /> : <span className="text-ink-soft">n/a</span>}
        </td>
        <td className="py-2.5 text-center">
          <Mark ok={row.passed} />
        </td>
      </tr>
      {open && (
        <tr className="border-b border-rule bg-paper/60">
          <td colSpan={4} className="px-3 py-3 text-[0.95rem] text-ink-soft">
            <span className="font-semibold text-ink">Answer: </span>
            {stripMarkdown(row.answer)}
            {row.cited_docs.length > 0 && <span className="block pt-1 text-sm">Cited: {row.cited_docs.join(", ")}</span>}
          </td>
        </tr>
      )}
    </>
  );
}

export function AccuracyView() {
  const [token, setToken] = useAdminToken();
  const [state, setState] = useState<EvalState | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<EvalState>("/api/eval/latest")
      .then(setState)
      .catch((e: ApiError) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const running = state?.status.state === "running";
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [running, load]);

  async function runEval() {
    setError("");
    try {
      await api("/api/admin/eval", { method: "POST", adminToken: token });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? (e.status === 401 ? "That token didn't work." : e.message) : "Couldn't start the run.");
    }
  }

  const report = state?.report;
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="text-[1.6rem] font-bold tracking-tight">How accurate is it?</h1>
      <p className="mt-2 max-w-prose text-ink-soft">
        DocsDesk is tested on a fixed set of 32 questions: 26 the help center answers and 6 it doesn&apos;t, including one
        that tries to override its instructions. These numbers come from the last run on the live app, scored with simple
        checks you can verify row by row below.
      </p>

      {error && <p className="mt-4 text-margin">{error}</p>}
      {state?.status.state === "failed" && <p className="mt-4 text-margin">The last run failed: {state.status.error}</p>}
      {running && (
        <p className="mt-4 text-fern-deep" aria-live="polite">
          Running: {state.status.done} of {state.status.total} questions. It pauses between questions to stay inside the
          free API limits, so a full run takes a few minutes.
        </p>
      )}

      {!report && state && !running && <p className="mt-8 text-ink-soft">No results yet. Run the test set to see them here.</p>}

      {report && (
        <>
          <table className="mt-8 w-full border-collapse text-left">
            <caption className="pb-2 text-left text-sm text-ink-soft">
              {report.summary.passed} of {report.summary.total} questions passed. Run on{" "}
              {new Date(report.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })} with{" "}
              {report.chat_model}, top {report.top_k} sources, similarity cut-off {report.min_similarity}.
            </caption>
            <tbody>
              {METRICS.map((m) => (
                <tr key={m.key} className="border-b border-rule align-top first:border-t-2 first:border-t-ink">
                  <th scope="row" className="w-[40%] py-3 pr-4 font-semibold">
                    {m.label}
                  </th>
                  <td className="tabular w-20 py-3 pr-4 text-right text-xl font-bold">{pct(report.summary[m.key] as number | null)}</td>
                  <td className="py-3 text-[0.95rem] text-ink-soft">{m.explain}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2 className="mt-10 font-semibold">Every question</h2>
          <p className="text-sm text-ink-soft">Click a question to see the answer it got.</p>
          <table className="mt-3 w-full border-collapse text-left">
            <thead>
              <tr className="border-b-2 border-ink text-sm">
                <th className="py-2 pr-3 font-semibold">Question</th>
                <th className="py-2 pr-3 text-center font-semibold">Right source</th>
                <th className="py-2 pr-3 text-center font-semibold">Key fact</th>
                <th className="py-2 text-center font-semibold">Passed</th>
              </tr>
            </thead>
            <tbody>
              {report.rows.map((row) => (
                <RowDetail key={row.id} row={row} />
              ))}
            </tbody>
          </table>
        </>
      )}

      <div className="mt-10 border-t border-rule pt-6">
        <h2 className="font-semibold">Run the test set again</h2>
        <p className="mb-3 mt-1 text-sm text-ink-soft">Needs the admin token, since every run uses API quota.</p>
        <TokenField token={token} onSave={setToken} />
        {token && (
          <button
            onClick={runEval}
            disabled={running}
            className="mt-3 rounded-md bg-fern px-4 py-2 font-semibold text-sheet hover:bg-fern-deep disabled:opacity-50"
          >
            {running ? "Running..." : "Run 32 questions"}
          </button>
        )}
      </div>
    </div>
  );
}
