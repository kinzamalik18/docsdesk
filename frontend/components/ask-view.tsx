"use client";

import { useEffect, useRef, useState } from "react";

import { Entry, type EntryData } from "@/components/entry";
import { api, ApiError, SLOW_REQUEST_MS, type ChatResponse, type Info, type SourceDoc } from "@/lib/api";

const SAMPLE_QUESTIONS = [
  "Can I get a refund on my annual plan?",
  "What happens if an automatic card charge fails?",
  "Can I get two-factor codes by SMS?",
  "My client never got the invoice email. What should I check?",
  "Do you have an iPhone app?",
];

export function AskView() {
  const [entries, setEntries] = useState<EntryData[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<Info | null>(null);
  const [sources, setSources] = useState<SourceDoc[] | null>(null);
  const [sourcesError, setSourcesError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(0);

  useEffect(() => {
    api<Info>("/api/info").then(setInfo).catch(() => {});
    api<SourceDoc[]>("/api/sources")
      .then(setSources)
      .catch((e: ApiError) => setSourcesError(e.message));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries]);

  const update = (id: string, patch: Partial<EntryData>) =>
    setEntries((all) => all.map((e) => (e.id === id ? { ...e, ...patch } : e)));

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    nextId.current += 1;
    const id = `e${nextId.current}`;
    setEntries((all) => [...all, { id, question: q }]);
    setQuestion("");
    setBusy(true);
    const slowTimer = setTimeout(() => update(id, { slow: true }), SLOW_REQUEST_MS);
    try {
      const response = await api<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ question: q }) });
      update(id, { response });
    } catch (e) {
      update(id, { error: e instanceof ApiError ? e.message : "Something went wrong. Try again." });
    } finally {
      clearTimeout(slowTimer);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid w-full max-w-6xl flex-1 gap-0 lg:grid-cols-[22rem_1fr]">
      <aside className="order-last border-t border-rule px-4 py-8 sm:px-6 lg:order-none lg:border-r lg:border-t-0 lg:pr-8">
        <h1 className="text-[1.6rem] font-bold leading-tight tracking-tight">
          Answers from the help center, with the source for every fact.
        </h1>
        <p className="mt-3 text-ink-soft">
          DocsDesk searches Fernbill&apos;s help articles, answers only from what they say, and numbers each source. When the
          articles don&apos;t cover something, it says so instead of guessing.
        </p>

        <h2 className="mt-8 hidden font-semibold lg:block">Try a question</h2>
        <ul className="mt-2 hidden space-y-1 lg:block">
          {SAMPLE_QUESTIONS.map((q) => (
            <li key={q}>
              <button
                onClick={() => ask(q)}
                disabled={busy}
                className="w-full rounded-md px-2 py-1.5 text-left text-[0.95rem] text-fern-deep hover:bg-paper disabled:opacity-50"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>

        <h2 className="mt-8 font-semibold">
          Help articles it can read{sources ? <span className="tabular font-normal text-ink-soft"> ({sources.length})</span> : null}
        </h2>
        {sourcesError && <p className="mt-2 text-sm text-margin">{sourcesError}</p>}
        {!sources && !sourcesError && <p className="mt-2 text-sm text-ink-soft">Loading...</p>}
        {sources && (
          <ul className="mt-2 columns-1 text-sm text-ink-soft sm:columns-2 lg:columns-1">
            {sources.map((s) => (
              <li key={s.doc_id} className="break-inside-avoid py-0.5">
                {s.title}
              </li>
            ))}
          </ul>
        )}
        {info && (
          <p className="mt-8 text-sm text-ink-soft">
            Model: {info.chat_model}. Search: vector plus keyword, {info.persistent_store ? "Postgres with pgvector" : "in memory"}.
          </p>
        )}
      </aside>

      <section className="ledger order-first flex min-h-[70vh] flex-col lg:order-none" aria-label="Conversation">
        <div className="flex-1 pt-[var(--ledger-line)]">
          {entries.length === 0 ? (
            <div className="flex">
              <span className="w-[var(--margin-w)] shrink-0" />
              <div className="max-w-prose pl-4 pr-4">
                <p className="leading-[var(--ledger-line)] text-ink-soft">
                  Ask anything about using Fernbill. Numbers in red point to the help article behind each fact. Click one to
                  see the exact passage.
                </p>
                <ul className="lg:hidden">
                  {SAMPLE_QUESTIONS.map((q) => (
                    <li key={q}>
                      <button
                        onClick={() => ask(q)}
                        disabled={busy}
                        className="text-left leading-[var(--ledger-line)] text-fern-deep underline decoration-rule underline-offset-4 disabled:opacity-50"
                      >
                        {q}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            entries.map((entry) => <Entry key={entry.id} entry={entry} />)
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
          className="sticky bottom-0 flex gap-2 border-t border-rule bg-sheet/95 p-3 backdrop-blur sm:p-4"
        >
          <label htmlFor="question" className="sr-only">
            Your question
          </label>
          <input
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={1000}
            placeholder="For example: how do I add a team member?"
            className="min-w-0 flex-1 rounded-md border border-rule bg-sheet px-3 py-2 text-ink placeholder:text-ink-soft/70 focus:border-fern"
          />
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className="rounded-md bg-fern px-4 py-2 font-semibold text-sheet hover:bg-fern-deep disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </section>
    </div>
  );
}
