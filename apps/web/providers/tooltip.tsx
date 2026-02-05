"use client";

import { TooltipProvider as UITooltipProvider } from "@ai-router/ui/tooltip";

export function TooltipProvider({
  children,
  delayDuration = 0,
  ...props
}: React.ComponentProps<typeof UITooltipProvider>) {
  return (
    <UITooltipProvider delayDuration={delayDuration} {...props}>
      {children}
    </UITooltipProvider>
  );
}
