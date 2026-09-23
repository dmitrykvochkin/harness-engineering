import { NavPageHeader } from "@/components/nav-page-header";

export default function ToolErrorsSignalsPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader
        title="Tool Errors"
        description="Runs with failed or unexpected tool outcomes."
      />
      <div className="text-sm text-muted-foreground">Content coming soon.</div>
    </div>
  );
}
