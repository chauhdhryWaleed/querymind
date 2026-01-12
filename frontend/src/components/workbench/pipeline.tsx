"use client";

import { Check, Circle, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Stage, StreamStatus } from "@/lib/use-query-stream";

const STEPS: { node: string; label: string; hint: string }[] = [
  { node: "schema", label: "Retrieve schema", hint: "Finding the relevant tables" },
  { node: "generate", label: "Generate SQL", hint: "Drafting a query from your question" },
  { node: "validate", label: "Validate", hint: "Parsing & EXPLAIN-checking the SQL" },
  { node: "execute", label: "Execute", hint: "Running it read-only on your database" },
  { node: "interpret", label: "Interpret", hint: "Summarizing the result" },
];

type StepState = "done" | "active" | "failed" | "pending";

export function Pipeline({
  stages,
  status,
}: {
  stages: Stage[];
  status: StreamStatus;
}) {
  const order = STEPS.map((s) => s.node);
  const corrected = stages.some((s) => s.node === "correct");
  // Furthest pipeline node we've received a completion event for (-1 = none yet).
  const maxSeen = stages.reduce((m, s) => Math.max(m, order.indexOf(s.node)), -1);

  function stateOf(node: string): StepState {
    const idx = order.indexOf(node);
    if (status === "done") return "done";
    if (status === "running") {
      if (idx <= maxSeen) return "done";
      if (idx === maxSeen + 1) return "active";
      return "pending";
    }
    if (status === "error") {
      const failingIdx = Math.min(maxSeen + 1, order.length - 1);
      if (idx < failingIdx) return "done";
      if (idx === failingIdx) return "failed";
    }
    return "pending";
  }

  return (
    <div className="mx-auto w-full max-w-md py-6">
      <ol className="relative">
        {STEPS.map((step, i) => {
          const state = stateOf(step.node);
          const isLast = i === STEPS.length - 1;
          return (
            <li key={step.node} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "grid size-12 shrink-0 place-items-center rounded-full border-2 transition-colors",
                    state === "done" && "border-success bg-success/10 text-success",
                    state === "active" && "border-primary bg-primary/10 text-primary",
                    state === "failed" && "border-destructive bg-destructive/10 text-destructive",
                    state === "pending" && "border-border bg-muted/40 text-muted-foreground",
                  )}
                >
                  {state === "done" ? (
                    <Check className="size-6" />
                  ) : state === "active" ? (
                    <Loader2 className="size-6 animate-spin" />
                  ) : state === "failed" ? (
                    <X className="size-6" />
                  ) : (
                    <Circle className="size-5" />
                  )}
                </div>
                {!isLast && (
                  <div
                    className={cn(
                      "my-1 w-0.5 flex-1 rounded-full transition-colors",
                      state === "done" ? "bg-success/60" : "bg-border",
                    )}
                  />
                )}
              </div>

              <div className={cn("pb-6", isLast && "pb-0")}>
                <p
                  className={cn(
                    "text-base font-medium leading-tight transition-colors",
                    state === "pending" ? "text-muted-foreground" : "text-foreground",
                  )}
                >
                  {step.label}
                </p>
                <p
                  className={cn(
                    "mt-0.5 text-sm",
                    state === "active" ? "text-primary" : "text-muted-foreground",
                  )}
                >
                  {state === "done"
                    ? "Done"
                    : state === "active"
                      ? `${step.hint}…`
                      : state === "failed"
                        ? "Failed"
                        : step.hint}
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      {corrected && (
        <div className="mt-2 flex justify-center">
          <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs font-medium text-warning">
            self-corrected
          </span>
        </div>
      )}
    </div>
  );
}
