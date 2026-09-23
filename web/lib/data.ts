import "server-only";

import {
  allocateSlug,
  toSignalDefinition,
  validateSignalDefinition,
  type SignalDefinition,
} from "./signal-definitions";
import {
  latestSignals,
  toIssue,
  toSignal,
  type Issue,
  type RunDetail,
  type RunInfo,
  type Signal,
  type TraceEvent,
} from "./types";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY;

const SIGNAL_COLUMNS =
  "id,run_id,signal_type,verdict,explanation,evidence_event_ids,detector_version,created_at";

async function rest<T>(
  path: string,
  init?: { method?: "GET" | "POST" | "DELETE"; body?: unknown },
): Promise<T> {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY");
  }

  const res = await fetch(`${SUPABASE_URL.replace(/\/$/, "")}/rest/v1/${path}`, {
    method: init?.method ?? "GET",
    headers: {
      apikey: SUPABASE_PUBLISHABLE_KEY,
      Authorization: `Bearer ${SUPABASE_PUBLISHABLE_KEY}`,
      ...(init?.method === "POST" || init?.method === "DELETE" ? { Prefer: "return=representation" } : {}),
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
    },
    body: init?.body ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });

  const json = (await res.json().catch(() => null)) as { message?: string } | T | null;
  if (!res.ok) {
    const message =
      json && typeof json === "object" && "message" in json && json.message
        ? json.message
        : `Could not load data (${res.status})`;
    throw new Error(message);
  }
  return json as T;
}

export async function getRunStarts(): Promise<{ runId: string; startTime: string }[]> {
  const rows = await rest<{ run_id: string; start_time: string | null }[]>(
    "runs?select=run_id,start_time&start_time=not.is.null&order=start_time.asc&limit=1000",
  );
  return rows.flatMap((row) =>
    row.start_time ? [{ runId: row.run_id, startTime: row.start_time }] : [],
  );
}

export async function getSignals(): Promise<Signal[]> {
  const rows = await rest<Record<string, unknown>[]>(
    `signals?select=${SIGNAL_COLUMNS}&order=created_at.desc&limit=1000`,
  );
  return latestSignals(rows.map(toSignal).filter((row): row is Signal => row !== null));
}

export async function getRun(runId: string): Promise<RunDetail> {
  const filter = encodeURIComponent(runId);
  const [runs, events, signals] = await Promise.all([
    rest<RunInfo[]>(
      `runs?select=run_id,agent_version,start_time,duration_ms,environment&run_id=eq.${filter}`,
    ),
    rest<TraceEvent[]>(
      `events?select=id,seq,type,role,content,tool_name,status,timestamp&run_id=eq.${filter}&order=seq.asc`,
    ),
    rest<Record<string, unknown>[]>(
      `signals?select=${SIGNAL_COLUMNS}&run_id=eq.${filter}&order=created_at.desc`,
    ),
  ]);

  const run = runs[0];
  if (!run) throw new Error("Run not found");

  return {
    run,
    events,
    signals: latestSignals(signals.map(toSignal).filter((row): row is Signal => row !== null)),
  };
}

export async function getIssues(): Promise<Issue[]> {
  const rows = await rest<Record<string, unknown>[]>("issues?select=*&order=created_at.desc&limit=100");
  return rows.map(toIssue);
}

const DEFINITION_COLUMNS = "id,title,prompt,slug,created_at";

export async function getSignalDefinitions(): Promise<SignalDefinition[]> {
  const rows = await rest<Record<string, unknown>[]>(
    `signal_definitions?select=${DEFINITION_COLUMNS}&order=created_at.asc`,
  );
  return rows.flatMap((row) => {
    const definition = toSignalDefinition(row);
    return definition ? [definition] : [];
  });
}

export async function getSignalDefinition(slug: string): Promise<SignalDefinition | null> {
  const rows = await rest<Record<string, unknown>[]>(
    `signal_definitions?select=${DEFINITION_COLUMNS}&slug=eq.${encodeURIComponent(slug)}&limit=1`,
  );
  return rows[0] ? toSignalDefinition(rows[0]) : null;
}

export async function createSignalDefinition(input: {
  title: string;
  prompt: string;
}): Promise<{ ok: true; slug: string } | { ok: false; error: string }> {
  const validated = validateSignalDefinition(input);
  if (!validated.ok) return validated;

  const existing = await getSignalDefinitions();
  const slug = allocateSlug(
    validated.title,
    existing.map((definition) => definition.slug),
  );
  if (!slug) return { ok: false, error: "Title needs at least one letter or number." };

  try {
    await rest<Record<string, unknown>[]>("signal_definitions", {
      method: "POST",
      body: { title: validated.title, prompt: validated.prompt, slug },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not save this signal.";
    return { ok: false, error: message };
  }

  return { ok: true, slug };
}

export async function deleteSignalDefinition(
  slug: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const rows = await rest<Record<string, unknown>[]>(
      `signal_definitions?slug=eq.${encodeURIComponent(slug)}`,
      { method: "DELETE" },
    );
    if (!Array.isArray(rows) || rows.length === 0) {
      return { ok: false, error: "This signal was already deleted." };
    }
    return { ok: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not delete this signal.";
    return { ok: false, error: message };
  }
}
