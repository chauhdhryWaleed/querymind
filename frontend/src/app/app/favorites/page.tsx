"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Star, Copy, Trash2, Play } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { PageContainer } from "@/components/page-container";
import { EmptyState } from "@/components/empty-state";
import { useFavorites } from "@/lib/hooks";
import { api } from "@/lib/api";

export default function FavoritesPage() {
  const router = useRouter();
  const { data, isLoading } = useFavorites();
  const qc = useQueryClient();
  const del = useMutation({
    mutationFn: (id: string) => api(`/favorites/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites"] });
      toast.success("Removed");
    },
  });
  const items = data?.items ?? [];

  return (
    <div>
      <PageHeader title="Favorites" description="Saved queries you can re-run." />
      <PageContainer className="space-y-3">
        {isLoading ? (
          [0, 1].map((i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : !items.length ? (
          <EmptyState icon={Star} title="No saved queries" description="Save a result from the workbench to keep it here." />
        ) : (
          items.map((f) => (
            <Card key={f.id}>
              <CardContent className="space-y-2 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{f.name}</p>
                    {f.question && <p className="text-sm text-muted-foreground">{f.question}</p>}
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => router.push(`/app/workbench?q=${encodeURIComponent(f.question || f.name)}`)}
                    >
                      <Play className="size-3.5" /> Run
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Copy SQL"
                      onClick={() => {
                        navigator.clipboard.writeText(f.sql);
                        toast.success("SQL copied");
                      }}
                    >
                      <Copy className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label="Delete" onClick={() => del.mutate(f.id)}>
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  </div>
                </div>
                <pre className="whitespace-pre-wrap break-words rounded-md bg-muted/40 p-3 font-mono text-xs leading-relaxed">{f.sql}</pre>
              </CardContent>
            </Card>
          ))
        )}
      </PageContainer>
    </div>
  );
}
