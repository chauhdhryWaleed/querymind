"use client";

import * as React from "react";
import { streamQuery, type StreamEvent } from "./sse";
import type { QueryResponse } from "./types";

export type Stage = {
  node: string;
  label: string;
  payload: Record<string, unknown>;
  at: number;
};

export type StreamStatus = "idle" | "running" | "done" | "error";

const PIPELINE = ["schema", "generate", "validate", "execute", "interpret"];

export function useQueryStream() {
  const [status, setStatus] = React.useState<StreamStatus>("idle");
  const [stages, setStages] = React.useState<Stage[]>([]);
  const [result, setResult] = React.useState<QueryResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  // Kept so the result card can save the favorite with the real question text, not the request id.
  const [question, setQuestion] = React.useState<string>("");
  const controllerRef = React.useRef<AbortController | null>(null);

  const run = React.useCallback(
    (params: { connectionId: string; question: string; llmKeyId?: string | null }) => {
      controllerRef.current?.abort();
      setStatus("running");
      setStages([]);
      setResult(null);
      setError(null);
      setQuestion(params.question);

      controllerRef.current = streamQuery(
        {
          connection_id: params.connectionId,
          question: params.question,
          llm_key_id: params.llmKeyId ?? null,
          session_id: sessionId,
        },
        {
          onEvent: (evt: StreamEvent) => {
            if (evt.type === "meta") setSessionId(evt.data.session_id);
            else if (evt.type === "stage")
              setStages((s) => [
                ...s,
                { node: evt.data.node, label: evt.data.label, payload: evt.data.payload, at: Date.now() },
              ]);
            else if (evt.type === "result") {
              setResult(evt.data as unknown as QueryResponse);
              setStatus("done");
            } else if (evt.type === "error") {
              setError(evt.data.message);
              setStatus("error");
            }
          },
          onError: (err) => {
            setError(err.message);
            setStatus("error");
          },
        },
      );
    },
    [sessionId],
  );

  const abort = React.useCallback(() => {
    controllerRef.current?.abort();
    setStatus("idle");
  }, []);

  React.useEffect(() => () => controllerRef.current?.abort(), []);

  return { status, stages, result, error, run, abort, sessionId, question, pipeline: PIPELINE };
}
