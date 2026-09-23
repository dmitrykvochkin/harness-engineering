import "server-only";

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

async function rest<T>(path: string): Promise<T> {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY");
  }

  const res = await fetch(`${SUPABASE_URL.replace(/\/$/, "")}/rest/v1/${path}`, {
    headers: {
      apikey: SUPABASE_PUBLISHABLE_KEY,
      Authorization: `Bearer ${SUPABASE_PUBLISHABLE_KEY}`,
    },
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
