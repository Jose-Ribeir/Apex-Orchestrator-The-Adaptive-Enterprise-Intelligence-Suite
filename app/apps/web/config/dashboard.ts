import type {
  NavMainItem,
  NavSecondaryItem,
  ProjectItem,
  SidebarTeam,
  SidebarUser,
} from "@/types/dashboard";
import type { LucideIcon } from "lucide-react";
import {
  AudioWaveform,
  BookOpen,
  Bot,
  Command,
  Frame,
  GalleryVerticalEnd,
  LifeBuoy,
  Map,
  PieChart,
  Send,
  Settings2,
  SquareTerminal,
} from "lucide-react";

export const sidebarIconMap: Record<string, LucideIcon> = {
  AudioWaveform,
  BookOpen,
  Bot,
  Command,
  Frame,
  GalleryVerticalEnd,
  LifeBuoy,
  Map,
  PieChart,
  Send,
  Settings2,
  SquareTerminal,
};

export const defaultTeams: SidebarTeam[] = [
  { name: "GeminiMesh", logo: GalleryVerticalEnd, plan: "Enterprise" },
];

export const defaultNavMain: NavMainItem[] = [
  {
    title: "Playground",
    url: "#",
    icon: "SquareTerminal",
    defaultOpen: true,
    items: [
      { title: "History", url: "#" },
      { title: "Starred", url: "#" },
      { title: "Settings", url: "#", isActive: true },
    ],
  },
  {
    title: "Models",
    url: "#",
    icon: "Bot",
    defaultOpen: true,
    items: [
      { title: "Genesis", url: "#" },
      { title: "Explorer", url: "#" },
      { title: "Quantum", url: "#" },
    ],
  },
  {
    title: "Documentation",
    url: "#",
    icon: "BookOpen",
    items: [
      { title: "Introduction", url: "#" },
      { title: "Get Started", url: "#" },
      { title: "Tutorials", url: "#" },
      { title: "Changelog", url: "#" },
    ],
  },
  {
    title: "Settings",
    url: "#",
    icon: "Settings2",
    items: [
      { title: "General", url: "#" },
      { title: "Team", url: "#" },
      { title: "Billing", url: "#" },
      { title: "Limits", url: "#" },
    ],
  },
];

export const defaultNavSecondary: NavSecondaryItem[] = [
  { title: "Support", url: "#", icon: "LifeBuoy" },
  { title: "Feedback", url: "#", icon: "Send" },
];

export const defaultProjects: ProjectItem[] = [
  { name: "Design Engineering", url: "#", icon: "Frame" },
  { name: "Sales & Marketing", url: "#", icon: "PieChart" },
  { name: "Travel", url: "#", icon: "Map" },
];

export const defaultSidebarUser: SidebarUser = {
  name: "shadcn",
  email: "m@example.com",
  avatar: "/avatars/shadcn.jpg",
};
