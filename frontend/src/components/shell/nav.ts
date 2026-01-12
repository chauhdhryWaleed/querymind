import {
  Database,
  History,
  KeyRound,
  Settings,
  Star,
  TerminalSquare,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

/** Primary app navigation, shared by the desktop sidebar and the mobile drawer. */
export const NAV: NavItem[] = [
  { href: "/app/workbench", label: "Workbench", icon: TerminalSquare },
  { href: "/app/connections", label: "Connections", icon: Database },
  { href: "/app/keys", label: "LLM Keys", icon: KeyRound },
  { href: "/app/history", label: "History", icon: History },
  { href: "/app/favorites", label: "Favorites", icon: Star },
  { href: "/app/settings/account", label: "Settings", icon: Settings },
];
