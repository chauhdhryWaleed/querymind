"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/page-container";
import { useStats } from "@/lib/hooks";
import { formatProvider } from "@/lib/format";

export default function UsagePage() {
  const { data, isLoading } = useStats(30);

  const stats = data && [
    { label: "Queries (30d)", value: data.query_count },
    { label: "Successful", value: data.successful_query_count },
    { label: "Failed", value: data.failed_query_count },
    { label: "Avg latency", value: `${Math.round(data.avg_execution_time_ms)}ms` },
    { label: "Avg retries", value: data.avg_retry_count.toFixed(2) },
    { label: "Input tokens", value: data.total_input_tokens.toLocaleString() },
    { label: "Output tokens", value: data.total_output_tokens.toLocaleString() },
    { label: "👍 / 👎", value: `${data.feedback_up} / ${data.feedback_down}` },
  ];

  return (
    <PageContainer>
      <p className="mb-4 text-sm text-muted-foreground">Activity across the last 30 days.</p>
      <div>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {stats?.map((s) => (
                <Card key={s.label}>
                  <CardContent className="py-5">
                    <p className="text-xs text-muted-foreground">{s.label}</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums">{s.value}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
            {data?.providers?.length ? (
              <div className="mt-6">
                <h2 className="mb-2 text-sm font-medium capitalize">By provider</h2>
                <div className="space-y-2">
                  {data.providers.map((p) => (
                    <Card key={p.provider}>
                      <CardContent className="flex items-center justify-between py-3 text-sm">
                        <span className="font-medium">{formatProvider(p.provider)}</span>
                        <span className="text-muted-foreground">
                          {p.query_count} queries ·{" "}
                          {(p.input_tokens + p.output_tokens).toLocaleString()} tokens
                        </span>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
    </PageContainer>
  );
}
