"use server";

import { revalidatePath } from "next/cache";

import { createSignalDefinition, deleteSignalDefinition } from "@/lib/data";

export type CreateSignalState = {
  error: string | null;
  slug: string | null;
};

export async function createSignalAction(
  _previous: CreateSignalState,
  formData: FormData,
): Promise<CreateSignalState> {
  const result = await createSignalDefinition({
    title: String(formData.get("title") ?? ""),
    prompt: String(formData.get("prompt") ?? ""),
  });

  if (!result.ok) return { error: result.error, slug: null };

  revalidatePath("/", "layout");
  return { error: null, slug: result.slug };
}

export async function deleteSignalAction(
  slug: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const result = await deleteSignalDefinition(slug);
  if (!result.ok) return result;

  revalidatePath("/", "layout");
  return { ok: true };
}
