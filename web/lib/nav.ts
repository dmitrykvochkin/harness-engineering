import {
  Bug,
  Inbox,
  Radar,
  TrendingDown,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export type NavSubItem = {
  title: string;
  url: string;
  icon?: LucideIcon;
};

export type NavItem = {
  title: string;
  url: string;
  icon: LucideIcon;
  subItems?: NavSubItem[];
};

export const navItems: NavItem[] = [
  {
    title: "Inbox",
    url: "/inbox",
    icon: Inbox,
  },
  {
    title: "Signals",
    url: "/signals",
    icon: Radar,
    subItems: [
      { title: "Negative", url: "/signals/negative", icon: TrendingDown },
      { title: "Tool Errors", url: "/signals/tool-errors", icon: Wrench },
    ],
  },
  {
    title: "Issues",
    url: "/issues",
    icon: Bug,
  },
];
