"use client";

import { type LucideIcon } from "lucide-react";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@ai-router/ui/sidebar";

export interface NavProjectsProps {
  projects: { name: string; url: string; icon?: LucideIcon }[];
  groupLabel?: string;
}

export function NavProjects({
  projects,
  groupLabel = "Projects",
}: NavProjectsProps) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{groupLabel}</SidebarGroupLabel>
      <SidebarMenu>
        {projects.map((item) => (
          <SidebarMenuItem key={item.name}>
            <SidebarMenuButton asChild tooltip={item.name}>
              <a href={item.url}>
                {item.icon ? <item.icon className="size-4" /> : null}
                <span>{item.name}</span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
