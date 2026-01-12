/** SSE consumer for POST /query/stream. EventSource can't POST, so we stream the
 * fetch response and parse the event/data frames; returns an AbortController. */
import { API_BASE, loadCsrfToken } from "./api";

export type StreamEvent =
  | { type: "meta"; data: { session_id: string; request_id: string } }
  | { type: "stage"; data: { node: string; label: string; payload: Record<string, unknown> } }
  | { type: "result"; data: Record<string, unknown> }
  | { type: "error"; data: { message: string } };

interface StreamHandlers {
  onEvent: (event: StreamEvent) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
}

export function streamQuery(
  body: { connection_id: string; question: string; llm_key_id?: string | null; session_id?: string | null },
  { onEvent, onDone, onError }: StreamHandlers,
): AbortController {
  const controller = new AbortController();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const csrf = loadCsrfToken();
  if (csrf) headers["X-CSRF-Token"] = csrf;

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Stream failed (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const evt = parseFrame(frame);
          if (evt) onEvent(evt);
        }
      }
      onDone?.();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onError?.(err as Error);
    }
  })();

  return controller;
}

function parseFrame(frame: string): StreamEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    return { type: event as StreamEvent["type"], data: JSON.parse(dataLines.join("\n")) } as StreamEvent;
  } catch {
    return null;
  }
}
