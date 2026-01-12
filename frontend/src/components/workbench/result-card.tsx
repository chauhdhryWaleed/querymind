"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Copy,
  Download,
  ThumbsDown,
  ThumbsUp,
  Star,
  ChevronDown,
  Clock,
  Rows3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { BarChart3 } from "lucide-react";
import { ChartView, resolveChart } from "./chart-view";
import { api } from "@/lib/api";
import { formatProvider } from "@/lib/format";
import type { QueryResponse } from "@/lib/types";

export function ResultCard({
  result,
  question,
  sessionId,
}: {
  result: QueryResponse;
  question: string;
  sessionId?: string | null;
}) {
  const rows = (result.results ?? []) as Record<string, unknown>[];
  const cols = result.columns ?? [];
  const meta = result.metadata;
  const chart = resolveChart(result.visualization, cols, rows);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  async function sendFeedback(rating: "up" | "down") {
    setFeedback(rating);
    try {
      await api(`/query/${meta.request_id}/feedback`, {
        method: "POST",
        body: { rating, session_id: sessionId ?? null },
      });
      toast.success("Thanks for the feedback");
    } catch {
      setFeedback(null);
      toast.error("Couldn't record feedback");
    }
  }

  async function saveFavorite() {
    const name = prompt("Name this saved query:", question.slice(0, 60) || result.sql.slice(0, 40));
    if (!name) return;
    try {
      await api("/favorites", {
        method: "POST",
        body: { name, question: question || name, sql: result.sql },
      });
      toast.success("Saved to favorites");
    } catch {
      toast.error("Couldn't save");
    }
  }

  function exportAs(fmt: "csv" | "json") {
    const content =
      fmt === "json"
        ? JSON.stringify(rows, null, 2)
        : toCsv(cols, rows);
    const blob = new Blob([content], { type: fmt === "json" ? "application/json" : "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `result.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Card className="overflow-hidden">
      {result.answer && (
        <div className="border-b p-5">
          <p className="text-sm leading-relaxed">{result.answer}</p>
        </div>
      )}

      <div className="border-b">
        <div className="flex items-center justify-between px-4 py-2">
          <span className="text-xs font-medium text-muted-foreground">SQL</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              navigator.clipboard.writeText(result.sql);
              toast.success("SQL copied");
            }}
          >
            <Copy className="size-3.5" /> Copy
          </Button>
        </div>
        <pre className="whitespace-pre-wrap break-words bg-muted/40 px-4 py-3 font-mono text-xs leading-relaxed">
          {result.sql}
        </pre>
      </div>

      {chart && (
        <div className="border-b">
          <div className="flex items-center gap-1.5 px-4 pt-3 text-xs font-medium text-muted-foreground">
            <BarChart3 className="size-3.5" /> Chart
          </div>
          <ChartView hint={result.visualization} columns={cols} rows={rows} />
        </div>
      )}

      <div>
        <div className="flex items-center justify-between gap-2 px-4 pt-3">
          <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
            <Rows3 className="size-3.5" /> Table
          </span>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Rows3 className="size-3" /> {result.row_count} rows
            </span>
            <span className="flex items-center gap-1">
              <Clock className="size-3" /> {Math.round(result.execution_time_ms)}ms
            </span>
          </div>
        </div>
        <DataTable columns={cols} rows={rows} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3">
        <div className="flex items-center gap-1">
          <Button
            variant={feedback === "up" ? "secondary" : "ghost"}
            size="icon"
            aria-label="Good answer"
            onClick={() => sendFeedback("up")}
          >
            <ThumbsUp className="size-4" />
          </Button>
          <Button
            variant={feedback === "down" ? "secondary" : "ghost"}
            size="icon"
            aria-label="Bad answer"
            onClick={() => sendFeedback("down")}
          >
            <ThumbsDown className="size-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={saveFavorite}>
            <Star className="size-4" /> Save
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <Download className="size-4" /> Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => exportAs("csv")}>CSV</DropdownMenuItem>
              <DropdownMenuItem onClick={() => exportAs("json")}>JSON</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {meta.retry_count > 0 && (
            <Badge variant="warning">
              {meta.retry_count} {meta.retry_count === 1 ? "retry" : "retries"}
            </Badge>
          )}
          <span>{(meta.input_tokens + meta.output_tokens).toLocaleString()} tokens</span>
          <span aria-hidden>·</span>
          <span>{formatProvider(meta.llm_provider)}</span>
        </div>
      </div>

      {meta.retrieval && <RetrievalPane retrieval={meta.retrieval} />}
    </Card>
  );
}

function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  if (!rows.length)
    return <p className="p-6 text-sm text-muted-foreground">No rows returned.</p>;
  return (
    <div className="max-h-96 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-muted/60 text-left">
          <tr>
            {columns.map((c) => (
              <th key={c} className="whitespace-nowrap px-4 py-2 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t transition-colors hover:bg-muted/40">
              {columns.map((c) => (
                <td key={c} className="whitespace-nowrap px-4 py-1.5 font-mono text-xs">
                  {formatCell(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RetrievalPane({
  retrieval,
}: {
  retrieval: NonNullable<QueryResponse["metadata"]["retrieval"]>;
}) {
  return (
    <details className="border-t bg-muted/20 px-4 py-3 text-xs">
      <summary className="flex cursor-pointer items-center gap-1 font-medium text-muted-foreground">
        <ChevronDown className="size-3" /> Retrieval: {retrieval.tables.length} tables,{" "}
        {retrieval.schema_tokens} schema tokens
      </summary>
      <table className="mt-2 w-full font-mono">
        <tbody>
          {retrieval.tables.map((t) => (
            <tr key={t.name} className="text-muted-foreground">
              <td className="py-0.5 pr-4 text-foreground">{t.name}</td>
              <td className="py-0.5 pr-4">{t.via}</td>
              <td className="py-0.5 pr-4">lex {t.lexical.toFixed(2)}</td>
              <td className="py-0.5 pr-4">vec {t.vector.toFixed(2)}</td>
              <td className="py-0.5">→ {t.score.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "∅";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function toCsv(columns: string[], rows: Record<string, unknown>[]): string {
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.join(","), ...rows.map((r) => columns.map((c) => esc(r[c])).join(","))].join("\n");
}
