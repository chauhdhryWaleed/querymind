"use client";

import { forwardRef } from "react";
import { ArrowUp, Database, Square } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Modern AI-chat composer: one rounded surface holding an auto-growing textarea
 * and an inline action row. Enter submits, Shift+Enter inserts a newline. The
 * whole surface lights up on focus; the send button is the only primary accent.
 */
export const Composer = forwardRef<
  HTMLTextAreaElement,
  {
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
    onStop: () => void;
    running: boolean;
    canSend: boolean;
    disabled?: boolean;
    placeholder?: string;
    connectionName?: string;
  }
>(function Composer(
  { value, onChange, onSubmit, onStop, running, canSend, disabled, placeholder, connectionName },
  ref,
) {
  return (
    <div
      className={cn(
        "group flex flex-col gap-1.5 rounded-[1.75rem] border bg-card/90 p-2 shadow-lg backdrop-blur-sm",
        "transition-[border-color,box-shadow] duration-200",
        "focus-within:border-ring/70 focus-within:shadow-xl focus-within:ring-2 focus-within:ring-ring/25",
        disabled && "opacity-60",
      )}
    >
      <textarea
        ref={ref}
        rows={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
        placeholder={placeholder}
        className={cn(
          "max-h-48 w-full resize-none bg-transparent px-3 pt-2 text-[0.95rem] leading-relaxed outline-none",
          "placeholder:text-muted-foreground/70 disabled:cursor-not-allowed",
          "[field-sizing:content] min-h-[1.5rem]",
        )}
      />

      <div className="flex items-center justify-between gap-2 pl-2.5 pr-1">
        <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
          {connectionName ? (
            <>
              <Database className="size-3.5 shrink-0 opacity-70" />
              <span className="truncate">{connectionName}</span>
            </>
          ) : (
            <span className="truncate">No connection</span>
          )}
          <span className="mx-1 hidden text-border sm:inline">·</span>
          <span className="hidden sm:inline">
            <kbd className="rounded border border-border bg-muted px-1 py-px font-mono text-[10px]">
              Enter
            </kbd>{" "}
            to send
          </span>
        </div>

        {running ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-secondary-foreground transition-colors hover:bg-secondary/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <Square className="size-3.5 fill-current" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSend}
            aria-label="Send"
            className={cn(
              "grid size-8 shrink-0 place-items-center rounded-full transition-all duration-150 active:scale-95",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              canSend
                ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90"
                : "cursor-not-allowed bg-muted text-muted-foreground",
            )}
          >
            <ArrowUp className="size-4" />
          </button>
        )}
      </div>
    </div>
  );
});
