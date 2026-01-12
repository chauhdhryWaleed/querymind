"use client";

import { ArrowUpRight, PieChart, Sparkles, TrendingUp, Trophy, type LucideIcon } from "lucide-react";
import { useExamples } from "@/lib/hooks";

const CATEGORY_ICON: Record<string, LucideIcon> = {
  trends: TrendingUp,
  leaderboards: Trophy,
  distribution: PieChart,
  analytics: Sparkles,
};

/** Up to four ready-to-run starter questions, one per example category. */
export function SuggestedPrompts({ onPick }: { onPick: (text: string) => void }) {
  const { data } = useExamples();
  const picks = (data?.categories ?? [])
    .map((c) => ({ icon: CATEGORY_ICON[c.id] ?? Sparkles, text: c.queries[0]?.text }))
    .filter((p): p is { icon: LucideIcon; text: string } => Boolean(p.text))
    .slice(0, 4);

  if (!picks.length) return null;

  return (
    <div className="mt-8 grid w-full max-w-xl gap-2 sm:grid-cols-2">
      {picks.map(({ icon: Icon, text }) => (
        <button
          key={text}
          type="button"
          onClick={() => onPick(text)}
          className="group flex items-center gap-2.5 rounded-xl border bg-card/50 px-3.5 py-3 text-left text-sm transition-colors hover:border-ring/50 hover:bg-accent"
        >
          <Icon className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
          <span className="truncate text-foreground/90">{text}</span>
          <ArrowUpRight className="ml-auto size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </button>
      ))}
    </div>
  );
}
