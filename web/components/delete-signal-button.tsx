"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { deleteSignalAction } from "@/app/signals/actions";
import { Button } from "@/components/ui/button";

export function DeleteSignalButton({ slug }: { slug: string }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  if (!confirming) {
    return (
      <Button type="button" variant="destructive" onClick={() => setConfirming(true)}>
        Delete
      </Button>
    );
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex items-center gap-2">
        <Button type="button" variant="ghost" disabled={pending} onClick={() => setConfirming(false)}>
          Cancel
        </Button>
        <Button
          type="button"
          variant="destructive"
          disabled={pending}
          onClick={() => {
            setError(null);
            startTransition(async () => {
              const result = await deleteSignalAction(slug);
              if (!result.ok) {
                setError(result.error);
                return;
              }
              router.push("/signals");
              router.refresh();
            });
          }}
        >
          {pending ? "Deleting…" : "Delete signal"}
        </Button>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
