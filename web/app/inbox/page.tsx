import { NavPageHeader } from "@/components/nav-page-header";

export default function InboxPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader title="Inbox" description="Recent runs and conversations, newest first." />
      <div className="text-sm text-muted-foreground">Content coming soon.</div>
    </div>
  );
}
