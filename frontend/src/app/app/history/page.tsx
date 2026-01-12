"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Clock, History as HistoryIcon, Rows3, Copy, Play, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { PageContainer } from "@/components/page-container";
import { EmptyState } from "@/components/empty-state";
import { useHistory, useDeleteHistoryItem, useClearHistory } from "@/lib/hooks";
import { useConnectionContext } from "@/components/shell/connection-context";
import type { HistoryItem } from "@/lib/types";

export default function HistoryPage() {
  const router = useRouter();
  const { selectedId } = useConnectionContext();
  const { data, isLoading } = useHistory(selectedId ?? undefined);
  const del = useDeleteHistoryItem();
  const clear = useClearHistory();
  const turns = (data?.turns ?? []) as HistoryItem[];

  function runAgain(question: string) {
    router.push(`/app/workbench?q=${encodeURIComponent(question)}`);
  }

  function clearAll() {
    if (!confirm("Delete all query history for this connection? This can't be undone.")) return;
    clear.mutate(selectedId, { onSuccess: () => toast.success("History cleared") });
  }

  return (
    <div>
      <PageHeader
        title="History"
        description="Your recent queries on this connection."
        action={
          turns.length > 0 ? (
            <Button variant="outline" size="sm" onClick={clearAll} disabled={clear.isPending}>
              <Trash2 className="size-4" /> Clear history
            </Button>
          ) : undefined
        }
      />
      <PageContainer className="space-y-3">
        {isLoading ? (
          [0, 1, 2].map((i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : !turns.length ? (
          <EmptyState icon={HistoryIcon} title="No history yet" description="Run a query to see it here." />
        ) : (
          turns.map((t) => (
            <Card key={t.id}>
              <CardContent className="space-y-2.5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-medium leading-snug">{t.question}</p>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => runAgain(t.question)}>
                      <Play className="size-3.5" /> Run
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Copy SQL"
                      onClick={() => {
                        navigator.clipboard.writeText(t.final_sql);
                        toast.success("SQL copied");
                      }}
                    >
                      <Copy className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete"
                      onClick={() =>
                        del.mutate(t.id, { onSuccess: () => toast.success("Removed") })
                      }
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  </div>
                </div>

                {t.answer && (
                  <p className="text-sm leading-relaxed text-muted-foreground">{t.answer}</p>
                )}

                {t.final_sql && (
                  <pre className="whitespace-pre-wrap break-words rounded-md bg-muted/40 p-3 font-mono text-xs leading-relaxed">
                    {t.final_sql}
                  </pre>
                )}

                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Rows3 className="size-3" /> {t.row_count} rows
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="size-3" /> {Math.round(t.execution_time_ms)}ms
                  </span>
                  {t.retry_count > 0 && <Badge variant="warning">{t.retry_count} retries</Badge>}
                  <span>{new Date(t.created_at).toLocaleString()}</span>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </PageContainer>
    </div>
  );
}
