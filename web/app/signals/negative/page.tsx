import { NavPageHeader } from "@/components/nav-page-header";

export default function NegativeSignalsPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader
        title="Negative"
        description="Runs where users expressed frustration or dissatisfaction."
      />
      <div className="text-sm text-muted-foreground">Content coming soon.</div>
    </div>
  );
}
