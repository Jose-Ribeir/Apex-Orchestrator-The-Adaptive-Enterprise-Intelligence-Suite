export default function Page() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid auto-rows-min gap-4 md:grid-cols-3">
        <div className="aspect-video rounded-xl border border-border bg-muted/80" />
        <div className="aspect-video rounded-xl border border-border bg-muted/80" />
        <div className="aspect-video rounded-xl border border-border bg-muted/80" />
      </div>
      <div className="min-h-[400px] flex-1 rounded-xl border border-border bg-muted/80" />
    </div>
  );
}
