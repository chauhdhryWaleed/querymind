import Link from "next/link";
import { Database } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 py-12">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[480px] opacity-70"
        style={{
          background:
            "radial-gradient(60% 70% at 50% 0%, color-mix(in oklch, var(--color-primary) 22%, transparent), transparent 70%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.4] [mask-image:radial-gradient(70%_50%_at_50%_0%,black,transparent)]"
        style={{
          backgroundImage:
            "linear-gradient(to right, var(--color-border) 1px, transparent 1px), linear-gradient(to bottom, var(--color-border) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <Link
        href="/"
        className="mb-8 flex items-center gap-2.5 text-lg font-semibold tracking-tight"
      >
        <span className="grid size-8 place-items-center rounded-md bg-primary text-primary-foreground shadow-sm">
          <Database className="size-4" />
        </span>
        QueryMind
      </Link>
      <div className="w-full max-w-md">{children}</div>
      <p className="mt-8 max-w-sm text-center text-xs leading-relaxed text-muted-foreground">
        Connect your own database, bring your own LLM key. Read-only by default,
        AST-validated, EXPLAIN-checked.
      </p>
    </div>
  );
}
