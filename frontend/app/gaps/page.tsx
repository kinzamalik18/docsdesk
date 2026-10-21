import type { Metadata } from "next";

import { GapsView } from "@/components/gaps-view";

export const metadata: Metadata = { title: "Missing docs · DocsDesk" };

export default function GapsPage() {
  return <GapsView />;
}
