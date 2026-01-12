"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Database, Plus, RefreshCw, Plug, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { PageContainer } from "@/components/page-container";
import { EmptyState } from "@/components/empty-state";
import { DemoConnectionButton } from "@/components/connections/demo-connection-button";
import {
  useConnections,
  useDeleteConnection,
  useReloadSchema,
  useTestConnection,
} from "@/lib/hooks";
import { formatStatus } from "@/lib/format";

const STATUS: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  ready: "success",
  indexing: "warning",
  pending: "warning",
  failed: "destructive",
};

export default function ConnectionsPage() {
  const { data: connections, isLoading } = useConnections();
  const test = useTestConnection();
  const reload = useReloadSchema();
  const del = useDeleteConnection();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function onTest(id: string) {
    setBusyId(id);
    try {
      const r = await test.mutateAsync(id);
      r.ok
        ? toast.success(`Connected: ${r.server_version?.split(" ").slice(0, 2).join(" ")} (${r.latency_ms}ms)`)
        : toast.error(r.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Connections"
        description="Databases the agent can query. Read-only by default."
        action={
          <Button asChild>
            <Link href="/app/connections/new">
              <Plus className="size-4" /> New connection
            </Link>
          </Button>
        }
      />
      <PageContainer className="space-y-3">
        {isLoading ? (
          [0, 1].map((i) => <Skeleton key={i} className="h-20 w-full" />)
        ) : !connections?.length ? (
          <EmptyState
            icon={Database}
            title="No connections yet"
            description="Connect a Postgres database to start asking questions, or try the bundled demo dataset."
            action={
              <div className="flex flex-col items-center gap-2 sm:flex-row">
                <Button asChild>
                  <Link href="/app/connections/new">
                    <Plus className="size-4" /> New connection
                  </Link>
                </Button>
                <DemoConnectionButton />
              </div>
            }
          />
        ) : (
          connections.map((c) => (
            <Card key={c.id}>
              <CardContent className="flex items-center justify-between gap-4 py-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">{c.name}</span>
                    <Badge variant={STATUS[c.index_status] ?? "secondary"}>
                      {formatStatus(c.index_status)}
                    </Badge>
                    {c.read_only && <Badge variant="outline">read-only</Badge>}
                  </div>
                  <p className="mt-0.5 truncate text-sm text-muted-foreground">
                    {c.username}@{c.host}:{c.port}/{c.database}
                  </p>
                  {c.index_error && (
                    <p className="mt-0.5 truncate text-xs text-destructive">{c.index_error}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button variant="ghost" size="sm" onClick={() => onTest(c.id)} disabled={busyId === c.id}>
                    {busyId === c.id ? <Loader2 className="size-4 animate-spin" /> : <Plug className="size-4" />}
                    Test
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => reload.mutate(c.id, { onSuccess: () => toast.success("Re-indexing queued") })}
                  >
                    <RefreshCw className="size-4" /> Reload
                  </Button>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/app/connections/${c.id}/edit`}>Edit</Link>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete"
                    onClick={() => {
                      if (confirm(`Delete connection "${c.name}"?`))
                        del.mutate(c.id, { onSuccess: () => toast.success("Deleted") });
                    }}
                  >
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </PageContainer>
    </div>
  );
}
