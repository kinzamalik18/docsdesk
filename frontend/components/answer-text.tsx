import { Fragment } from "react";

/** Models often add markdown bold for menu names. Snippets show plain text. */
export function stripMarkdown(text: string): string {
  return text.replace(/\*\*(.+?)\*\*/g, "$1").replace(/__(.+?)__/g, "$1");
}

/** Renders bold markdown and turns the bracketed numbers into links to their footnotes. */
export function AnswerText({ text, entryId }: { text: string; entryId: string }) {
  const parts = text.split(/(\[\d{1,2}\]|\*\*.+?\*\*)/g);
  return (
    <p className="text-[1.05rem] leading-[var(--ledger-line)]">
      {parts.map((part, i) => {
        const citation = part.match(/^\[(\d{1,2})\]$/);
        if (citation) {
          return (
            <a
              key={i}
              href={`#${entryId}-src-${citation[1]}`}
              aria-label={`Source ${citation[1]}`}
              className="tabular mx-0.5 align-super text-[0.72rem] font-semibold text-margin hover:underline"
            >
              {citation[1]}
            </a>
          );
        }
        const bold = part.match(/^\*\*(.+?)\*\*$/);
        if (bold) return <strong key={i} className="font-semibold">{bold[1]}</strong>;
        return <Fragment key={i}>{part}</Fragment>;
      })}
    </p>
  );
}
