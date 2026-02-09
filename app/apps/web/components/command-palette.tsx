"use client";

import { Bot, KeyRound, Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import * as React from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getPlatformNavForCommand, getSettingsNav } from "@/config/nav";
import { agentModeLabel } from "@/lib/format";
import { useActiveAgent } from "@/providers/active-agent";
import { useUser } from "@/providers/user";
import type { AgentInfo } from "@ai-router/client";
import { listAgentsOptions } from "@ai-router/client/react-query";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@ai-router/ui/command";
import { useQuery } from "@tanstack/react-query";

const AGENT_SUB_PATH =
  /^\/agents\/([^/]+)\/(instructions|tools|queries|stats|documents)$/;

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { agentId, setAgentId } = useActiveAgent();
  const { setTheme } = useTheme();
  const user = useUser();

  const handleSwitchAgent = React.useCallback(
    (newAgentId: string | null) => {
      setAgentId(newAgentId);
      const match = pathname?.match(AGENT_SUB_PATH);
      if (match && newAgentId) {
        const subPath = match[2];
        navigate(`/agents/${newAgentId}/${subPath}`, { replace: true });
      }
      onOpenChange(false);
    },
    [pathname, navigate, setAgentId, onOpenChange],
  );

  const { data: agentsData } = useQuery({
    ...listAgentsOptions({}),
    enabled: Boolean(user?.id) && open,
  });
  const agents: AgentInfo[] = React.useMemo(
    () => (agentsData as { agents?: AgentInfo[] } | undefined)?.agents ?? [],
    [agentsData],
  );

  const agentBase = agentId ? `/agents/${agentId}` : null;
  const platformItems = React.useMemo(
    () => getPlatformNavForCommand(agentBase),
    [agentBase],
  );
  const settingsItems = getSettingsNav();

  const handleSelect = React.useCallback(
    (url: string) => {
      navigate(url);
      onOpenChange(false);
    },
    [navigate, onOpenChange],
  );

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search or run a command..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Platform">
          {platformItems.map((item) => (
            <CommandItem
              key={item.title + item.url}
              value={item.title}
              onSelect={() => handleSelect(item.url)}
            >
              <item.icon className="size-4 shrink-0" />
              <span>{item.title}</span>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Agents">
          {agents.map((agent) => (
            <CommandItem
              key={agent.agent_id ?? agent.name}
              value={`Switch to ${agent.name}`}
              onSelect={() => handleSwitchAgent(agent.agent_id ?? null)}
            >
              <Bot className="size-4 shrink-0" />
              <span>Switch to {agent.name}</span>
              {agent.mode && (
                <CommandShortcut>{agentModeLabel(agent.mode)}</CommandShortcut>
              )}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Settings">
          {settingsItems.map((item) => (
            <CommandItem
              key={item.title}
              value={item.title}
              onSelect={() => handleSelect(item.url)}
            >
              <item.icon className="size-4 shrink-0" />
              <span>{item.title}</span>
            </CommandItem>
          ))}
          <CommandItem
            value="API Keys"
            onSelect={() => handleSelect("/settings/api-tokens")}
          >
            <KeyRound className="size-4 shrink-0" />
            <span>API Keys</span>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Theme">
          <CommandItem
            value="Theme Light"
            onSelect={() => {
              setTheme("light");
              onOpenChange(false);
            }}
          >
            <Sun className="size-4 shrink-0" />
            <span>Light</span>
          </CommandItem>
          <CommandItem
            value="Theme Dark"
            onSelect={() => {
              setTheme("dark");
              onOpenChange(false);
            }}
          >
            <Moon className="size-4 shrink-0" />
            <span>Dark</span>
          </CommandItem>
          <CommandItem
            value="Theme System"
            onSelect={() => {
              setTheme("system");
              onOpenChange(false);
            }}
          >
            <Monitor className="size-4 shrink-0" />
            <span>System</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
