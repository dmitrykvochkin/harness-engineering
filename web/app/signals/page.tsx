import { NavPageHeader } from "@/components/nav-page-header";

export default function SignalsPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader title="Signals" description="Detected behavioural signals across runs." />
      <div className="text-sm text-muted-foreground">Content coming soon.</div>
    </div>
  );
}
