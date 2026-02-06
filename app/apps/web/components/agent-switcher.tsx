"use client";

import { CreateAgentForm } from "@/components/create-agent-form";
import { useActiveAgent } from "@/providers/active-agent";
import { useUser } from "@/providers/user";
import type { Agent } from "@ai-router/client";
import { listAgentsOptions } from "@ai-router/client/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@ai-router/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@ai-router/ui/sheet";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@ai-router/ui/sidebar";
import { useQuery } from "@tanstack/react-query";
import { Bot, ChevronsUpDown, Plus } from "lucide-react";
import * as React from "react";
import { useLocation, useNavigate } from "react-router-dom";

const AGENT_SUB_PATH =
  /^\/agents\/([^/]+)\/(instructions|tools|queries|stats)$/;

export function AgentSwitcher() {
  const { isMobile } = useSidebar();
  const { agentId, setAgentId } = useActiveAgent();
  const user = useUser();
  const pathname = useLocation().pathname;
  const navigate = useNavigate();
  const [addAgentOpen, setAddAgentOpen] = React.useState(false);

  const handleSwitchAgent = React.useCallback(
    (newAgentId: string | null) => {
      setAgentId(newAgentId);
      const match = pathname?.match(AGENT_SUB_PATH);
      if (match && newAgentId) {
        const subPath = match[2];
        navigate(`/agents/${newAgentId}/${subPath}`, { replace: true });
      }
    },
    [pathname, navigate, setAgentId],
  );

  const { data: agentsData, isPending } = useQuery({
    ...listAgentsOptions({}),
    enabled: Boolean(user?.id),
  });
  const agents = React.useMemo(
    () => (agentsData as { data?: Agent[] } | undefined)?.data ?? [],
    [agentsData],
  );
  const activeAgent = agentId
    ? agents.find((a) => a.id === agentId)
    : (agents[0] ?? null);

  // Sync active agent with list: set to first agent when none selected, or clear when current id is not in list
  React.useEffect(() => {
    if (agents.length === 0) return;
    const firstId = agents[0]?.id ?? null;
    const currentInList = agentId
      ? agents.some((a) => a.id === agentId)
      : false;
    if (!agentId || !activeAgent) {
      setAgentId(firstId);
    } else if (!currentInList) {
      setAgentId(firstId);
    }
  }, [agentId, agents, activeAgent, setAgentId]);

  if (isPending && agents.length === 0) {
    return (
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" className="gap-2">
            <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
              <Bot className="size-4" />
            </div>
            <span className="truncate text-sm text-muted-foreground">
              Loading…
            </span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    );
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                <Bot className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">
                  {activeAgent?.name ?? "No agent"}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {activeAgent?.mode ?? "Select an agent"}
                </span>
              </div>
              <ChevronsUpDown className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
            align="start"
            side={isMobile ? "bottom" : "right"}
            sideOffset={4}
          >
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Agents
            </DropdownMenuLabel>
            {agents
              .filter((agent) => agent.id !== agentId)
              .map((agent) => (
                <DropdownMenuItem
                  key={agent.id}
                  onClick={() => handleSwitchAgent(agent.id ?? null)}
                  className="gap-2 p-2"
                >
                  <div className="flex size-6 items-center justify-center rounded-sm border">
                    <Bot className="size-4 shrink-0" />
                  </div>
                  <span className="truncate">{agent.name}</span>
                  <span className="ml-auto truncate text-xs text-muted-foreground">
                    {agent.mode}
                  </span>
                </DropdownMenuItem>
              ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="gap-2"
              onClick={() => setAddAgentOpen(true)}
            >
              <div className="flex size-6 shrink-0 items-center justify-center rounded-sm border border-current/20">
                <Plus className="size-4 shrink-0" />
              </div>
              <span className="font-medium">Add agent</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Sheet open={addAgentOpen} onOpenChange={setAddAgentOpen}>
          <SheetContent side="right" className="w-full max-w-md sm:max-w-md">
            <SheetHeader>
              <SheetTitle>Add agent</SheetTitle>
            </SheetHeader>
            <div className="mt-6">
              <CreateAgentForm
                title=""
                description=""
                showHeader={false}
                submitLabel="Create agent"
                onSuccess={() => setAddAgentOpen(false)}
              />
            </div>
          </SheetContent>
        </Sheet>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
