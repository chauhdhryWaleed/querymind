"use client";

import * as React from "react";
import { useConnections } from "@/lib/hooks";
import type { ConnectionOut } from "@/lib/types";

interface ConnectionCtx {
  connections: ConnectionOut[];
  isLoading: boolean;
  selectedId: string | null;
  setSelectedId: (id: string) => void;
  selected: ConnectionOut | null;
}

const Ctx = React.createContext<ConnectionCtx | null>(null);
const STORAGE_KEY = "selected_connection";

export function ConnectionProvider({ children }: { children: React.ReactNode }) {
  const { data: connections = [], isLoading } = useConnections();
  const [selectedId, setSelectedIdState] = React.useState<string | null>(null);

  // Restore last selection, defaulting to the first connection.
  React.useEffect(() => {
    if (selectedId || connections.length === 0) return;
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const valid = stored && connections.some((c) => c.id === stored) ? stored : connections[0].id;
    setSelectedIdState(valid);
  }, [connections, selectedId]);

  const setSelectedId = React.useCallback((id: string) => {
    setSelectedIdState(id);
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, id);
  }, []);

  const selected = connections.find((c) => c.id === selectedId) ?? null;

  return (
    <Ctx.Provider value={{ connections, isLoading, selectedId, setSelectedId, selected }}>
      {children}
    </Ctx.Provider>
  );
}

export function useConnectionContext() {
  const ctx = React.useContext(Ctx);
  if (!ctx) throw new Error("useConnectionContext must be used within ConnectionProvider");
  return ctx;
}
