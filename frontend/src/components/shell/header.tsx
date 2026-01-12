"use client";

import { useRouter } from "next/navigation";
import { Database, LogOut, PanelLeft, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "./theme-toggle";
import { MobileNav } from "./mobile-nav";
import { useConnectionContext } from "./connection-context";
import { useLogout, useMe } from "@/lib/hooks";
import { formatStatus } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  ready: "success",
  indexing: "warning",
  pending: "warning",
  failed: "destructive",
};

const STATUS_DOT: Record<string, string> = {
  ready: "bg-success",
  indexing: "bg-warning animate-pulse",
  pending: "bg-warning animate-pulse",
  failed: "bg-destructive",
};

export function Header({ onToggleSidebar }: { onToggleSidebar?: () => void }) {
  const router = useRouter();
  const { connections, selectedId, setSelectedId, selected } = useConnectionContext();
  const { data: me } = useMe();
  const logout = useLogout();

  async function onLogout() {
    await logout.mutateAsync().catch(() => {});
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b bg-background/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center gap-2">
        <MobileNav />
        {onToggleSidebar && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Toggle sidebar"
            onClick={onToggleSidebar}
            className="hidden md:inline-flex"
          >
            <PanelLeft className="size-5" />
          </Button>
        )}
        {connections.length > 0 ? (
          <Select value={selectedId ?? undefined} onValueChange={setSelectedId}>
            <SelectTrigger className="h-9 w-[220px] gap-2">
              <Database className="size-4 text-muted-foreground" />
              <SelectValue placeholder="Select a connection" />
            </SelectTrigger>
            <SelectContent>
              {connections.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <span className="text-sm text-muted-foreground">No connections yet</span>
        )}
        {selected && (
          <Badge
            variant={STATUS_VARIANT[selected.index_status] ?? "secondary"}
            className="gap-1.5"
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                STATUS_DOT[selected.index_status] ?? "bg-muted-foreground",
              )}
            />
            {formatStatus(selected.index_status)}
          </Badge>
        )}
      </div>

      <div className="flex items-center gap-1">
        <ThemeToggle />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Account">
              <User className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel className="truncate">
              {me?.user.name || me?.user.email || "Account"}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onLogout} className="capitalize">
              <LogOut className="size-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
