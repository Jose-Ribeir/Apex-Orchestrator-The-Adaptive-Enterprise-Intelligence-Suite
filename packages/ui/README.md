# @ai-router/ui

Shared UI components (shadcn/ui) for the monorepo.

## Adding components

Shadcn is configured in this package. Run the CLI from `packages/ui` so new components are added here:

```bash
cd packages/ui
pnpm dlx shadcn@latest add <component-name>
# e.g. pnpm dlx shadcn@latest add dialog
```

New components are added under `src/` and use `./utils` for the `cn` helper. The consuming app (e.g. `apps/web`) must include this package in its Tailwind `content` so classes are generated.
