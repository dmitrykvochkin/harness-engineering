import "server-only";

import { toIssue, toSignal, type Issue, type Signal } from "./types";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY;

async function callEdgeFunction<T>(
  name: "signals" | "issues",
  searchParams?: URLSearchParams,
): Promise<T[]> {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error(
      "Missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY environment variables",
    );
  }

  const url = new URL(`${SUPABASE_URL.replace(/\/$/, "")}/functions/v1/${name}`);
  if (searchParams) {
    url.search = searchParams.toString();
  }

  const res = await fetch(url, {
    headers: { apikey: SUPABASE_PUBLISHABLE_KEY },
    // Read-only dashboard; fresh data on every server render.
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Edge function ${name} failed: ${res.status} ${body}`);
  }

  const json = (await res.json()) as { data?: unknown[] };
  return (json.data ?? []) as T[];
}

export async function getSignals(kind?: string): Promise<Signal[]> {
  const params = kind ? new URLSearchParams({ kind }) : undefined;
  const rows = await callEdgeFunction<Record<string, unknown>>(
    "signals",
    params,
  );
  return rows.map(toSignal);
}

export async function getIssues(): Promise<Issue[]> {
  const rows = await callEdgeFunction<Record<string, unknown>>("issues");
  return rows.map(toIssue);
}
