"use client";

import { useState } from "react";

import { AnswerText, stripMarkdown } from "@/components/answer-text";
import { api, type ChatResponse } from "@/lib/api";

export type EntryData = {
  id: string;
  question: string;
  response?: ChatResponse;
  error?: string;
  slow?: boolean;
};

function Margin({ children, red = false }: { children: React.ReactNode; red?: boolean }) {
  return (
    <span
      className={`tabular w-[var(--margin-w)] shrink-0 pr-3 text-right text-sm leading-[var(--ledger-line)] ${
        red ? "font-semibold text-margin" : "text-ink-soft"
      }`}
    >
      {children}
    </span>
  );
}

function Feedback({ entry }: { entry: EntryData }) {
  const [sent, setSent] = useState<"yes" | "no" | null>(null);
  if (!entry.response) return null;

  const send = (helpful: boolean) => {
    setSent(helpful ? "yes" : "no");
    api("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ question: entry.question, answer: entry.response!.answer, helpful }),
    }).catch(() => {
      /* feedback is best effort */
    });
  };

  if (sent) return <p className="text-sm leading-[var(--ledger-line)] text-ink-soft">Thanks, noted.</p>;
  return (
    <div className="flex items-center gap-2 text-sm leading-[var(--ledger-line)] text-ink-soft">
      <span>Was this helpful?</span>
      <button className="rounded px-2 hover:bg-sheet hover:text-ink" onClick={() => send(true)}>
        Yes
      </button>
      <button className="rounded px-2 hover:bg-sheet hover:text-ink" onClick={() => send(false)}>
        No
      </button>
    </div>
  );
}

function Footnote({ entryId, citation }: { entryId: string; citation: ChatResponse["citations"][number] }) {
  const [open, setOpen] = useState(false);
  const where = citation.section ? `${citation.doc_title} > ${citation.section}` : citation.doc_title;
  return (
    <li id={`${entryId}-src-${citation.number}`} className="flex scroll-mt-24">
      <Margin red>{citation.number}</Margin>
      <div className="min-w-0 flex-1 pl-4 pr-4">
        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="text-left text-[0.95rem] leading-[var(--ledger-line)] text-fern-deep underline decoration-rule underline-offset-4 hover:decoration-fern"
        >
          {where}
        </button>
        {open && (
          <blockquote className="enter my-1 border-l-2 border-fern bg-sheet/70 px-3 py-2 text-[0.92rem] leading-relaxed text-ink-soft">
            {stripMarkdown(citation.snippet)}
          </blockquote>
        )}
      </div>
    </li>
  );
}

export function Entry({ entry }: { entry: EntryData }) {
  const { response } = entry;
  return (
    <article className="pb-[var(--ledger-line)]" aria-label={`Question: ${entry.question}`}>
      <div className="flex">
        <Margin>You</Margin>
        <p className="flex-1 pl-4 pr-4 text-[1.05rem] font-semibold leading-[var(--ledger-line)]">{entry.question}</p>
      </div>

      <div className="flex">
        <Margin>Desk</Margin>
        <div className="min-w-0 flex-1 pl-4 pr-4" aria-live="polite">
          {!response && !entry.error && (
            <p className="leading-[var(--ledger-line)] text-ink-soft">
              {entry.slow
                ? "Waking up the server. Free hosting sleeps when nobody's using it, so this first answer can take up to a minute."
                : "Looking through the help docs..."}
            </p>
          )}
          {entry.error && <p className="leading-[var(--ledger-line)] text-margin">{entry.error}</p>}
          {response && (
            <div className="enter">
              <AnswerText text={response.answer} entryId={entry.id} />
              {!response.answered && (
                <p className="text-sm leading-[var(--ledger-line)] text-ink-soft">
                  This question was added to Missing docs, so the team can see which article to write next.
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {response && response.citations.length > 0 && (
        <ol className="enter" aria-label="Sources">
          {response.citations.map((c) => (
            <Footnote key={c.number} entryId={entry.id} citation={c} />
          ))}
        </ol>
      )}

      {response && (
        <div className="flex">
          <Margin>{""}</Margin>
          <div className="pl-4">
            <Feedback entry={entry} />
          </div>
        </div>
      )}
    </article>
  );
}
