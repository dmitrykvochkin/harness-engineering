import { NavPageHeader } from "@/components/nav-page-header";

export default function UserSettingsPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader title="User settings" description="Your profile and preferences." />
      <div className="text-sm text-muted-foreground">Content coming soon.</div>
    </div>
  );
}
