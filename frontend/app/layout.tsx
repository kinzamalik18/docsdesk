import type { Metadata } from "next";
import Link from "next/link";

import { SiteNav } from "@/components/site-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocsDesk",
  description:
    "A support assistant that answers from your help docs, cites the article it used, and says so when the answer isn't there.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-sheet">
        <header className="border-b border-rule bg-sheet">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-xl font-bold tracking-tight text-ink">DocsDesk</span>
              <span className="text-sm text-ink-soft">for Fernbill, a fictional invoicing app</span>
            </Link>
            <SiteNav />
          </div>
        </header>
        <main className="flex flex-1 flex-col">{children}</main>
        <footer className="border-t border-rule px-4 py-4 text-center text-sm text-ink-soft sm:px-6">
          Demo project. Fernbill and its help docs are made up.{" "}
          <a
            className="underline decoration-rule underline-offset-4 hover:text-ink"
            href="https://github.com/kinzamalik18/docsdesk"
          >
            Source on GitHub
          </a>
        </footer>
      </body>
    </html>
  );
}
