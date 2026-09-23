import { NavPageHeader } from "@/components/nav-page-header";

export default function IssuesPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader
        title="Issues"
        description="Grouped failure patterns with affected runs and evidence."
      />
      <div className="text-sm text-muted-foreground">Content coming soon.</div>
    </div>
  );
}
