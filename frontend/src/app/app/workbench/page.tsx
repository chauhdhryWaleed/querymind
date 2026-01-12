"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Database,
  KeyRound,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { Composer } from "@/components/workbench/composer";
import { SuggestedPrompts } from "@/components/workbench/suggested-prompts";
import { Pipeline } from "@/components/workbench/pipeline";
import { ResultCard } from "@/components/workbench/result-card";
import { SchemaExplorer } from "@/components/workbench/schema-explorer";
import { useConnectionContext } from "@/components/shell/connection-context";
import { useLlmKeys } from "@/lib/hooks";
import { useQueryStream } from "@/lib/use-query-stream";

export default function WorkbenchPage() {
  const { connections, selected, isLoading } = useConnectionContext();
  const { data: keys = [], isLoading: keysLoading } = useLlmKeys();
  const stream = useQueryStream();
  const [question, setQuestion] = useState("");
  const composerRef = useRef<HTMLTextAreaElement>(null);
  // A ?q= question is queued here and fired only once the connection is ready.
  const pendingRunRef = useRef<string | null>(null);
  const consumedUrlRef = useRef(false);

  const [schemaOpen, setSchemaOpen] = useState(true);
  const [schemaWidth, setSchemaWidth] = useState(288);
  const widthRef = useRef(schemaWidth);

  useEffect(() => {
    if (localStorage.getItem("ui.schemaOpen") === "0") setSchemaOpen(false);
    const w = Number(localStorage.getItem("ui.schemaWidth"));
    if (w >= 240 && w <= 640) {
      setSchemaWidth(w);
      widthRef.current = w;
    }
  }, []);

  function toggleSchema() {
    setSchemaOpen((o) => {
      const next = !o;
      localStorage.setItem("ui.schemaOpen", next ? "1" : "0");
      return next;
    });
  }

  function startResize(e: React.MouseEvent) {
    e.preventDefault();
    document.body.classList.add("select-none", "cursor-col-resize");
    function onMove(ev: MouseEvent) {
      const w = Math.min(640, Math.max(240, window.innerWidth - ev.clientX));
      widthRef.current = w;
      setSchemaWidth(w);
    }
    function onUp() {
      document.body.classList.remove("select-none", "cursor-col-resize");
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      localStorage.setItem("ui.schemaWidth", String(widthRef.current));
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  const noConnections = !isLoading && connections.length === 0;
  const noKeys = !keysLoading && keys.length === 0;
  const indexing = selected?.index_status === "indexing" || selected?.index_status === "pending";
  const indexFailed = selected?.index_status === "failed";
  const ready = selected?.index_status === "ready";
  const running = stream.status === "running";
  const canSend = !!selected && ready && !!question.trim() && !running;

  function runQuestion(text: string) {
    const q = text.trim();
    if (!selected || !q || running || !ready) return;
    setQuestion("");
    stream.run({ connectionId: selected.id, question: q });
  }

  // Pick up a ?q= question (e.g. "Run" from History/Favorites) once, on mount.
  useEffect(() => {
    if (consumedUrlRef.current) return;
    consumedUrlRef.current = true;
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      setQuestion(q);
      pendingRunRef.current = q;
      window.history.replaceState(null, "", "/app/workbench");
    }
  }, []);

  // Fire the queued question as soon as the connection is ready.
  useEffect(() => {
    if (pendingRunRef.current && selected && ready && !running) {
      const q = pendingRunRef.current;
      pendingRunRef.current = null;
      setQuestion("");
      stream.run({ connectionId: selected.id, question: q });
    }
  }, [ready, selected, running, stream]);

  if (noConnections) {
    return (
      <Onboard
        icon={Database}
        title="Connect a database to get started"
        description="Add a Postgres connection. We index its schema so the agent only sees the tables relevant to each question."
        cta={{ href: "/app/connections/new", label: "Connect a database" }}
      />
    );
  }
  if (noKeys) {
    return (
      <Onboard
        icon={KeyRound}
        title="Add an LLM key"
        description="Bring your own Anthropic, OpenAI, or Gemini key. It's encrypted at rest and used only for your queries."
        cta={{ href: "/app/keys", label: "Add an LLM key" }}
      />
    );
  }

  function content() {
    if (indexing) {
      return (
        <Centered>
          <Loader2 className="size-10 animate-spin text-primary" />
          <h2 className="mt-4 text-lg font-medium">Indexing schema…</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            We&apos;re reading {selected?.name}&apos;s tables and columns so the agent only
            sees what&apos;s relevant. This usually takes a moment.
          </p>
        </Centered>
      );
    }
    if (indexFailed) {
      return (
        <Centered>
          <div className="grid size-12 place-items-center rounded-full bg-destructive/10">
            <AlertTriangle className="size-6 text-destructive" />
          </div>
          <h2 className="mt-4 text-lg font-medium">Schema indexing failed</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Open <Link href="/app/connections" className="text-primary hover:underline">Connections</Link>{" "}
            and hit “Reload” to try indexing again.
          </p>
        </Centered>
      );
    }
    if (running) {
      return (
        <div className="flex flex-1 flex-col items-center justify-center">
          <Pipeline stages={stream.stages} status={stream.status} />
        </div>
      );
    }
    if (stream.status === "error") {
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-4">
          <Pipeline stages={stream.stages} status={stream.status} />
          {stream.error && (
            <div className="w-full max-w-md rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {stream.error}
            </div>
          )}
        </div>
      );
    }
    if (stream.result && selected) {
      return (
        <div className="py-6">
          <ResultCard
            result={stream.result}
            question={stream.question}
            sessionId={stream.sessionId}
          />
        </div>
      );
    }
    return (
      <Centered>
        <div className="grid size-14 place-items-center rounded-2xl bg-primary/10 text-primary ring-1 ring-inset ring-primary/20">
          <Sparkles className="size-7" />
        </div>
        <h2 className="mt-5 text-2xl font-semibold tracking-tight">
          Ask {selected?.name ?? "your database"} anything
        </h2>
        <p className="mt-2 max-w-md text-balance text-sm text-muted-foreground">
          Describe what you want in plain English. The agent finds the relevant tables,
          writes read-only SQL, runs it, and explains the result.
        </p>
        <SuggestedPrompts onPick={runQuestion} />
      </Centered>
    );
  }

  return (
    <div className="relative flex h-[calc(100vh-3.5rem)]">
      <div className="relative flex min-w-0 flex-1 flex-col">
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 pb-44 pt-6">
            {content()}
          </div>
        </div>

        <div className="absolute inset-x-0 bottom-0">
          <div className="pointer-events-none h-20 bg-gradient-to-t from-background via-background/85 to-transparent" />
          <div className="bg-background pb-4">
            <div className="mx-auto w-full max-w-3xl px-4">
              <Composer
                ref={composerRef}
                value={question}
                onChange={setQuestion}
                onSubmit={() => runQuestion(question)}
                onStop={stream.abort}
                running={running}
                canSend={canSend}
                disabled={!selected}
                connectionName={selected?.name}
                placeholder={
                  !selected
                    ? "Select a connection first"
                    : indexing
                      ? "Indexing schema… you can ask once it's ready"
                      : `Ask ${selected.name} anything…`
                }
              />
              <p className="mt-2 text-center text-[11px] text-muted-foreground">
                QueryMind drafts read-only SQL and self-corrects. Review the SQL before
                trusting results.
              </p>
            </div>
          </div>
        </div>
      </div>

      {selected && schemaOpen && (
        <aside
          style={{ width: schemaWidth }}
          className="relative hidden shrink-0 border-l lg:flex"
        >
          <div
            onMouseDown={startResize}
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize schema panel"
            className="absolute left-0 top-0 z-10 h-full w-1.5 -translate-x-1/2 cursor-col-resize transition-colors hover:bg-primary/40"
          />
          <div className="flex h-full w-full flex-col">
            <div className="flex items-center justify-between border-b px-3 py-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Schema
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="size-7"
                aria-label="Hide schema panel"
                onClick={toggleSchema}
              >
                <PanelRightClose className="size-4" />
              </Button>
            </div>
            <div className="min-h-0 flex-1">
              <SchemaExplorer
                connectionId={selected.id}
                indexing={indexing}
                onInsert={(ref) => setQuestion((q) => (q ? `${q} ${ref}` : ref))}
              />
            </div>
          </div>
        </aside>
      )}

      {selected && !schemaOpen && (
        <Button
          variant="outline"
          size="sm"
          onClick={toggleSchema}
          aria-label="Show schema panel"
          className="absolute right-3 top-3 z-10 hidden lg:inline-flex"
        >
          <PanelRightOpen className="size-4" /> Schema
        </Button>
      )}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
      {children}
    </div>
  );
}

function Onboard({
  icon,
  title,
  description,
  cta,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  cta: { href: string; label: string };
}) {
  return (
    <div className="p-10">
      <EmptyState
        icon={icon}
        title={title}
        description={description}
        action={
          <Button asChild>
            <Link href={cta.href}>{cta.label}</Link>
          </Button>
        }
      />
    </div>
  );
}
