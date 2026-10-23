import { createContext, use, type ReactNode } from "react";

import { useApi, type ApiState, type Meta } from "../../api/client";

type MetaValue = ApiState<Meta> & { retry: () => void };

const MetaContext = createContext<MetaValue | null>(null);

export function MetaProvider({ children }: { children: ReactNode }) {
  const meta = useApi<Meta>("/api/meta");
  return <MetaContext value={meta}>{children}</MetaContext>;
}

export function useMeta(): MetaValue {
  const value = use(MetaContext);
  if (value === null) throw new Error("useMeta must be used inside MetaProvider");
  return value;
}

/** "gpt-5.4-mini-2026-03-17" → "gpt-5.4-mini" */
export function shortModelName(snapshot: string): string {
  return snapshot.replace(/-\d{4}-\d{2}-\d{2}$/, "");
}
