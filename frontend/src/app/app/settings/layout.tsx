"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/app/settings/account", label: "Account" },
  { href: "/app/settings/security", label: "Security" },
  { href: "/app/settings/preferences", label: "Preferences" },
  { href: "/app/settings/usage", label: "Usage" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div>
      <div className="border-b">
        <div className="mx-auto w-full max-w-5xl px-4 pt-5 sm:px-6">
          <h1 className="text-xl font-semibold capitalize tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your account, security, and workspace preferences.
          </p>
          <nav className="-mb-px mt-4 flex gap-1 overflow-x-auto">
            {TABS.map((t) => {
              const active = pathname === t.href;
              return (
                <Link
                  key={t.href}
                  href={t.href}
                  className={cn(
                    "whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium capitalize transition-colors",
                    active
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
      {children}
    </div>
  );
}
