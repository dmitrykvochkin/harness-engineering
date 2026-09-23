export type SignalDefinition = {
  id: string;
  title: string;
  prompt: string;
  slug: string;
  created_at: string | null;
};

/** Slugs already used by the built-in detectors in the left menu. */
const BUILT_IN_SLUGS = new Set(["user-frustration", "task-failure", "forgetting"]);

export type SignalDefinitionInput = {
  ok: true;
  title: string;
  prompt: string;
};

export type SignalDefinitionError = {
  ok: false;
  error: string;
};

export function slugFromTitle(title: string): string {
  return title
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function allocateSlug(title: string, taken: readonly string[]): string | null {
  const base = slugFromTitle(title);
  if (!base) return null;

  const used = new Set<string>([...BUILT_IN_SLUGS, ...taken]);
  if (!used.has(base)) return base;

  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) suffix += 1;
  return `${base}-${suffix}`;
}

export function validateSignalDefinition(input: {
  title: string;
  prompt: string;
}): SignalDefinitionInput | SignalDefinitionError {
  const title = input.title.trim();
  const prompt = input.prompt.trim();
  if (!title) return { ok: false, error: "Title is required." };
  if (title.length > 80) return { ok: false, error: "Title must be 80 characters or fewer." };
  if (!prompt) return { ok: false, error: "Prompt is required." };
  if (!slugFromTitle(title)) {
    return { ok: false, error: "Title needs at least one letter or number." };
  }
  return { ok: true, title, prompt };
}

export function toSignalDefinition(row: Record<string, unknown>): SignalDefinition | null {
  const title = String(row.title ?? "").trim();
  const prompt = String(row.prompt ?? "").trim();
  const slug = String(row.slug ?? "").trim();
  if (!title || !prompt || !slug) return null;
  return {
    id: String(row.id ?? ""),
    title,
    prompt,
    slug,
    created_at: (row.created_at as string | null) ?? null,
  };
}
