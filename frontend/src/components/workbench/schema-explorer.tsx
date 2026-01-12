"use client";

import { useState } from "react";
import { ChevronRight, KeyRound, Link2, Search, Table2, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useConnectionSchema } from "@/lib/hooks";

export function SchemaExplorer({
  connectionId,
  indexing,
  onInsert,
}: {
  connectionId: string;
  indexing: boolean;
  onInsert?: (text: string) => void;
}) {
  const { data, isLoading } = useConnectionSchema(connectionId, indexing);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const tables = (data?.tables ?? []).filter(
    (t) =>
      !q ||
      t.name.toLowerCase().includes(q.toLowerCase()) ||
      t.columns.some((c) => c.name.toLowerCase().includes(q.toLowerCase())),
  );

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-3">
        <div className="flex items-center gap-2 rounded-md border px-2">
          <Search className="size-3.5 opacity-50" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search tables, columns…"
            className="h-8 border-0 px-0 shadow-none focus-visible:ring-0"
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 text-sm">
        {isLoading || (indexing && !tables.length) ? (
          <div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Indexing Schema…
          </div>
        ) : !tables.length ? (
          <p className="p-3 text-xs text-muted-foreground">No tables.</p>
        ) : (
          tables.map((t) => (
            <div key={t.id}>
              <button
                onClick={() => setOpen((o) => ({ ...o, [t.id]: !o[t.id] }))}
                className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left hover:bg-accent"
              >
                <ChevronRight className={cn("size-3.5 transition-transform", open[t.id] && "rotate-90")} />
                <Table2 className="size-3.5 text-muted-foreground" />
                <span className="truncate font-medium">{t.name}</span>
                {t.row_count != null && (
                  <span className="ml-auto text-[10px] text-muted-foreground">~{t.row_count}</span>
                )}
              </button>
              {open[t.id] && (
                <div className="ml-6 border-l pl-2">
                  {t.columns.map((c) => (
                    <button
                      key={c.name}
                      onClick={() => onInsert?.(`${t.name}.${c.name}`)}
                      className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs hover:bg-accent"
                      title="Insert column reference"
                    >
                      {c.is_pk ? (
                        <KeyRound className="size-3 text-warning" />
                      ) : c.is_fk ? (
                        <Link2 className="size-3 text-primary" />
                      ) : (
                        <span className="size-3" />
                      )}
                      <span className="truncate">{c.name}</span>
                      <span className="ml-auto truncate text-muted-foreground">{c.data_type}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
