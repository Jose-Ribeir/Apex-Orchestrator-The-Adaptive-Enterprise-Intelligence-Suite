"use client";

import {
  Activity,
  BarChart3,
  Bot,
  FileStack,
  FileText,
  Link2,
  MessageSquare,
  Sliders,
  Wrench,
} from "lucide-react";
import * as React from "react";

import { AgentSwitcher } from "@/components/agent-switcher";
import { NavMain } from "@/components/nav-main";
import { NavUser } from "@/components/nav-user";
import { useActiveAgent } from "@/providers/active-agent";
import { useUser } from "@/providers/user";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@ai-router/ui/sidebar";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const user = useUser();
  const { agentId } = useActiveAgent();
  const sidebarUser = {
    name: user.name ?? "User",
    email: user.email ?? "",
    avatar: user.image ?? "",
  };

  const agentBase = agentId ? `/agents/${agentId}` : "#";
  const platformNav = [
    { title: "Chat", url: "/", icon: MessageSquare },
    { title: "Instructions", url: `${agentBase}/instructions`, icon: FileText },
    { title: "Knowledge Base", url: `${agentBase}/documents`, icon: FileStack },
    { title: "Tools", url: `${agentBase}/tools`, icon: Wrench },
    { title: "Queries", url: `${agentBase}/queries`, icon: BarChart3 },
    { title: "Stats", url: `${agentBase}/stats`, icon: Activity },
    { title: "Human tasks", url: "/human-tasks", icon: Sliders },
    { title: "Connections", url: "/connections", icon: Link2 },
  ];

  const settingsNav = [
    { title: "Agents", url: "/settings/agents", icon: Bot },
    { title: "Tools", url: "/tools", icon: Wrench },
  ];

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <AgentSwitcher />
      </SidebarHeader>
      <SidebarContent>
        <NavMain groupLabel="Platform" items={platformNav} />
        <NavMain groupLabel="Settings" items={settingsNav} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={sidebarUser} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
