"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useMe } from "@/lib/hooks";
import { ConnectionProvider } from "@/components/shell/connection-context";
import { Sidebar } from "@/components/shell/sidebar";
import { Header } from "@/components/shell/header";
import { CommandPalette } from "@/components/shell/command-palette";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: me, isLoading, isError } = useMe();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (isError) router.replace("/login");
  }, [isError, router]);

  useEffect(() => {
    if (localStorage.getItem("ui.sidebarCollapsed") === "1") setSidebarCollapsed(true);
  }, []);

  function toggleSidebar() {
    setSidebarCollapsed((c) => {
      const next = !c;
      localStorage.setItem("ui.sidebarCollapsed", next ? "1" : "0");
      return next;
    });
  }

  if (isLoading || isError || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <ConnectionProvider>
      <div className="flex min-h-screen">
        <Sidebar collapsed={sidebarCollapsed} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header onToggleSidebar={toggleSidebar} />
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
      <CommandPalette />
    </ConnectionProvider>
  );
}
