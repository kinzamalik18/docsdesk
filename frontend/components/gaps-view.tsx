"use client";

import { useCallback, useEffect, useState } from "react";

import { TokenField } from "@/components/token-field";
import { useAdminToken } from "@/lib/admin-token";
import { api, ApiError, type Gap } from "@/lib/api";

const REASONS: Record<string, string> = {
  no_close_match: "No article came close",
  model_said_not_in_docs: "Articles found, but none answered it",
  no_citation: "Answer had no source, so it was held back",
  bad_model_output: "Model reply couldn't be read",
};

function formatDate(iso: string) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function GapsView() {
  const [token, setToken] = useAdminToken();
  const [gaps, setGaps] = useState<Gap[] | null>(null);
  const [error, setError] = useState("");
  const [needsToken, setNeedsToken] = useState(false);

  const load = useCallback(() => {
    api<Gap[]>("/api/gaps", { adminToken: token })
      .then((data) => {
        setGaps(data);
        setNeedsToken(false);
        setError("");
      })
      .catch((e: ApiError) => {
        if (e.status === 401 || e.status === 503) setNeedsToken(true);
        setError(e.status === 401 && token ? "That token didn't work." : e.status === 401 ? "" : e.message);
      });
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="text-[1.6rem] font-bold tracking-tight">Missing docs</h1>
      <p className="mt-2 max-w-prose text-ink-soft">
        Every question DocsDesk couldn&apos;t answer from the help center lands here. Each one is a hint about which article
        to write or update next.
      </p>

      {needsToken && (
        <div className="mt-6">
          <p className="mb-2 text-sm text-ink-soft">This list shows what visitors typed, so it needs the admin token.</p>
          <TokenField token={token} onSave={setToken} />
        </div>
      )}
      {error && <p className="mt-4 text-margin">{error}</p>}

      {gaps && gaps.length === 0 && (
        <p className="mt-8 text-ink-soft">
          Nothing here yet. Questions the help center can&apos;t answer will appear as people ask them.
        </p>
      )}

      {gaps && gaps.length > 0 && (
        <>
          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-ink-soft">{gaps.length} unanswered {gaps.length === 1 ? "question" : "questions"}, newest first</p>
            <button onClick={load} className="text-sm text-fern-deep underline underline-offset-4">
              Refresh
            </button>
          </div>
          <table className="mt-2 w-full border-collapse text-left">
            <thead>
              <tr className="border-b-2 border-ink text-sm">
                <th className="py-2 pr-4 font-semibold">Question</th>
                <th className="hidden py-2 pr-4 font-semibold sm:table-cell">Why it wasn&apos;t answered</th>
                <th className="py-2 font-semibold">Asked</th>
              </tr>
            </thead>
            <tbody>
              {gaps.map((gap, i) => (
                <tr key={i} className="border-b border-rule align-top">
                  <td className="py-2.5 pr-4">
                    {gap.question}
                    <span className="mt-0.5 block text-sm text-ink-soft sm:hidden">
                      {REASONS[gap.reason] ?? gap.reason}
                    </span>
                  </td>
                  <td className="hidden py-2.5 pr-4 text-ink-soft sm:table-cell">{REASONS[gap.reason] ?? gap.reason}</td>
                  <td className="whitespace-nowrap py-2.5 text-sm text-ink-soft">{formatDate(gap.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
