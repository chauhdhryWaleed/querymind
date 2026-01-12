"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Database,
  KeyRound,
  History,
  Star,
  Settings,
  TerminalSquare,
  Search,
} from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";

const ITEMS = [
  { label: "Workbench", href: "/app/workbench", icon: TerminalSquare },
  { label: "Connections", href: "/app/connections", icon: Database },
  { label: "New connection", href: "/app/connections/new", icon: Database },
  { label: "LLM Keys", href: "/app/keys", icon: KeyRound },
  { label: "History", href: "/app/history", icon: History },
  { label: "Favorites", href: "/app/favorites", icon: Star },
  { label: "Settings", href: "/app/settings/account", icon: Settings },
];

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="overflow-hidden p-0">
        <Command className="[&_[cmdk-input]]:h-11">
          <div className="flex items-center border-b px-3">
            <Search className="size-4 opacity-50" />
            <Command.Input
              placeholder="Go to…"
              className="h-11 w-full bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          <Command.List className="max-h-80 overflow-y-auto p-1">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results.
            </Command.Empty>
            {ITEMS.map(({ label, href, icon: Icon }) => (
              <Command.Item
                key={href}
                value={label}
                onSelect={() => {
                  router.push(href);
                  setOpen(false);
                }}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-accent"
              >
                <Icon className="size-4 opacity-70" />
                {label}
              </Command.Item>
            ))}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
