"use client";

import * as React from "react";

import { AgentSwitcher } from "@/components/agent-switcher";
import { NavMain } from "@/components/nav-main";
import { NavUser } from "@/components/nav-user";
import { getPlatformNavForSidebar, getSettingsNav } from "@/config/nav";
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

  const agentBase = agentId ? `/agents/${agentId}` : null;
  const platformNav = getPlatformNavForSidebar(agentBase);
  const settingsNav = getSettingsNav();

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
