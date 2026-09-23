"use client";

import { useActionState, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { createSignalAction, type CreateSignalState } from "@/app/signals/actions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const initialState: CreateSignalState = { error: null, slug: null };

function CreateSignalForm({ onCreated }: { onCreated: () => void }) {
  const router = useRouter();
  const [state, formAction, pending] = useActionState(createSignalAction, initialState);

  useEffect(() => {
    if (!state.slug) return;
    router.refresh();
    onCreated();
  }, [state.slug, router, onCreated]);

  return (
    <form action={formAction} className="mt-4 grid gap-4">
      <label className="grid gap-1.5 text-sm font-medium">
        Title
        <Input name="title" required maxLength={80} placeholder="Late refund" autoFocus />
      </label>
      <label className="grid gap-1.5 text-sm font-medium">
        Prompt
        <textarea
          name="prompt"
          required
          rows={6}
          placeholder="The agent promised a refund and never sent it."
          className="min-h-28 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
        />
      </label>
      {state.error && <p className="text-sm text-destructive">{state.error}</p>}
      <div className="flex justify-end">
        <Button type="submit" disabled={pending}>
          {pending ? "Saving…" : "Create signal"}
        </Button>
      </div>
    </form>
  );
}

export function CreateSignalButton() {
  const [open, setOpen] = useState(false);
  const [formKey, setFormKey] = useState(0);
  const close = useCallback(() => {
    setOpen(false);
    setFormKey((key) => key + 1);
  }, []);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setFormKey((key) => key + 1);
      }}
    >
      <DialogTrigger asChild>
        <Button>Create new signal</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create new signal</DialogTitle>
          <DialogDescription>
            Save a title and prompt. Evaluation runs separately.
          </DialogDescription>
        </DialogHeader>
        <CreateSignalForm key={formKey} onCreated={close} />
      </DialogContent>
    </Dialog>
  );
}
