import { Bug, Inbox, Radar, type LucideIcon } from "lucide-react";

import { signalCatalog } from "./signals";

export type NavSubItem = {
  title: string;
  url: string;
  icon?: LucideIcon;
};

export type NavItem = {
  title: string;
  url: string;
  icon: LucideIcon;
  exact?: boolean;
  subItems?: NavSubItem[];
};

export const navItems: NavItem[] = [
  {
    title: "Inbox",
    url: "/signals",
    icon: Inbox,
    exact: true,
  },
  {
    title: "Signals",
    url: "/signals",
    icon: Radar,
    subItems: signalCatalog.map((signal) => ({
      title: signal.label,
      url: `/signals/${signal.slug}`,
      icon: signal.icon,
    })),
  },
  {
    title: "Issues",
    url: "/issues",
    icon: Bug,
  },
];
