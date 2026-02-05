import type { LucideIcon } from "lucide-react";

export interface NavMainSubItem {
  title: string;
  url: string;
  isActive?: boolean;
}

export interface NavMainItem {
  title: string;
  url: string;
  icon: string | LucideIcon;
  /** Open this collapsible by default */
  defaultOpen?: boolean;
  /** Deprecated: use defaultOpen. Kept for backward compatibility. */
  isActive?: boolean;
  items?: NavMainSubItem[];
}

export interface NavSecondaryItem {
  title: string;
  url: string;
  icon: string;
}

export interface ProjectItem {
  name: string;
  url: string;
  icon: string | LucideIcon;
}

export interface SidebarUser {
  name: string;
  email: string;
  avatar: string;
}

export interface SidebarTeam {
  name: string;
  logo: LucideIcon;
  plan: string;
}
