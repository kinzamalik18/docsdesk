"use client";

import { useSyncExternalStore } from "react";

const KEY = "docsdesk-admin-token";
const EVENT = "docsdesk-admin-token-change";

// Kept for this browser tab only. Storage can be unavailable (private windows,
// blocked site data), so every access is guarded and the pages still work.
function read(): string {
  try {
    return sessionStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}

function write(value: string) {
  try {
    if (value) sessionStorage.setItem(KEY, value);
    else sessionStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: the token just won't be remembered */
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void) {
  window.addEventListener(EVENT, onChange);
  return () => window.removeEventListener(EVENT, onChange);
}

export function useAdminToken(): [string, (value: string) => void] {
  // Server render and first paint have no token, so the static page matches on hydration.
  const token = useSyncExternalStore(subscribe, read, () => "");
  return [token, write];
}
