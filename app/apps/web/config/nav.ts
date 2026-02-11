import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BarChart3,
  Bot,
  FileStack,
  FileText,
  GitBranch,
  Link2,
  MessageSquare,
  Sliders,
  Wrench,
  ScrollText,
} from "lucide-react";

export type PlatformNavItem = {
  title: string;
  /** Static path (e.g. "/", "/human-tasks") or agent-relative segment (e.g. "instructions"). */
  path: string;
  icon: LucideIcon;
  /** If true, path is relative to agent base (e.g. "instructions" → `/agents/:id/instructions`). */
  agentScoped?: boolean;
};

export type SettingsNavItem = {
  title: string;
  path: string;
  icon: LucideIcon;
};

export const platformNavConfig: PlatformNavItem[] = [
  { title: "Chat", path: "/", icon: MessageSquare },
  {
    title: "Instructions",
    path: "instructions",
    icon: FileText,
    agentScoped: true,
  },
  {
    title: "Prompt",
    path: "prompt",
    icon: ScrollText,
    agentScoped: true,
  },
  {
    title: "Knowledge Base",
    path: "documents",
    icon: FileStack,
    agentScoped: true,
  },
  { title: "Tools", path: "tools", icon: Wrench, agentScoped: true },
  { title: "Router & usage", path: "router", icon: GitBranch, agentScoped: true },
  { title: "Queries", path: "queries", icon: BarChart3, agentScoped: true },
  { title: "Stats", path: "stats", icon: Activity, agentScoped: true },
  { title: "Human tasks", path: "/human-tasks", icon: Sliders },
];

export const settingsNavConfig: SettingsNavItem[] = [
  { title: "Agents", path: "/settings/agents", icon: Bot },
  { title: "Connections", path: "/settings/connections", icon: Link2 },
  { title: "Tools", path: "/tools", icon: Wrench },
];

export type ResolvedNavItem = {
  title: string;
  url: string;
  icon: LucideIcon;
};

/**
 * Resolve platform nav for the sidebar. All items are included; agent-scoped
 * items use `#` when there is no agent.
 */
export function getPlatformNavForSidebar(
  agentBase: string | null,
): ResolvedNavItem[] {
  return platformNavConfig.map((item) => ({
    title: item.title,
    url: item.agentScoped
      ? agentBase
        ? `${agentBase}/${item.path}`
        : "#"
      : item.path,
    icon: item.icon,
  }));
}

/**
 * Resolve platform nav for the command palette. Agent-scoped items are only
 * included when there is an agent.
 */
export function getPlatformNavForCommand(
  agentBase: string | null,
): ResolvedNavItem[] {
  return platformNavConfig
    .filter((item) => !item.agentScoped || agentBase)
    .map((item) => ({
      title: item.title,
      url: item.agentScoped ? `${agentBase}/${item.path}` : item.path,
      icon: item.icon,
    }));
}

/**
 * Settings nav items (same for sidebar and command).
 */
export function getSettingsNav(): ResolvedNavItem[] {
  return settingsNavConfig.map((item) => ({
    title: item.title,
    url: item.path,
    icon: item.icon,
  }));
}
