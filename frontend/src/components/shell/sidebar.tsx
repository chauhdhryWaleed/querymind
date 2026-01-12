"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV } from "./nav";

export function Sidebar({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname();
  return (
    <aside
      className={cn(
        "w-45 shrink-0 flex-col border-r border-sidebar-border bg-sidebar",
        collapsed ? "hidden" : "hidden md:flex",
      )}
    >
      <Link
        href="/app/workbench"
        className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4 font-semibold tracking-tight"
      >
        <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground shadow-sm">
          <Database className="size-4" />
        </span>
        QueryMind
      </Link>

      <nav className="flex-1 space-y-0.5 p-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium capitalize transition-colors duration-150",
                active
                  ? "bg-primary/10 text-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground",
              )}
            >
              <Icon
                className={cn(
                  "size-4 shrink-0 transition-colors",
                  active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                )}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center justify-between rounded-md px-2 py-1.5 text-xs text-muted-foreground">
          <span className="capitalize">Command menu</span>
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] font-medium">
            ⌘K
          </kbd>
        </div>
      </div>
    </aside>
  );
}
