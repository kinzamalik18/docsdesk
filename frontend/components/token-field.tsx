"use client";

import { useState } from "react";

export function TokenField({ token, onSave }: { token: string; onSave: (value: string) => void }) {
  const [value, setValue] = useState("");
  if (token) {
    return (
      <p className="text-sm text-ink-soft">
        Admin access is on for this tab.{" "}
        <button className="underline underline-offset-4 hover:text-ink" onClick={() => onSave("")}>
          Remove token
        </button>
      </p>
    );
  }
  return (
    <form
      className="flex max-w-md gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSave(value.trim());
      }}
    >
      <label htmlFor="admin-token" className="sr-only">
        Admin token
      </label>
      <input
        id="admin-token"
        type="password"
        autoComplete="off"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Admin token"
        className="min-w-0 flex-1 rounded-md border border-rule px-3 py-2"
      />
      <button className="rounded-md bg-ink px-4 py-2 font-semibold text-sheet hover:bg-fern-deep">Unlock</button>
    </form>
  );
}
