import { isSignalType, isVerdict, type SignalType, type Verdict } from "./signals";

export type Signal = {
  id: string;
  run_id: string;
  signal_type: SignalType;
  verdict: Verdict;
  explanation: string;
  evidence_event_ids: string[];
  detector_version: string;
  created_at: string | null;
};

export type Issue = {
  id: string;
  title: string | null;
  description: string | null;
  created_at: string | null;
  raw: Record<string, unknown>;
};

export type TraceEvent = {
  id: string;
  seq: number;
  type: string;
  role: string;
  content: string;
  tool_name: string | null;
  status: string | null;
  timestamp: string | null;
};

export type RunInfo = {
  run_id: string;
  agent_version: string | null;
  start_time: string | null;
  duration_ms: number | null;
  environment: string | null;
};

export type RunDetail = {
  run: RunInfo;
  events: TraceEvent[];
  signals: Signal[];
};

export function toSignal(row: Record<string, unknown>): Signal | null {
  const signalType = String(row.signal_type ?? "");
  const verdict = String(row.verdict ?? "");
  if (!isSignalType(signalType) || !isVerdict(verdict)) return null;
  const evidence = row.evidence_event_ids;
  return {
    id: String(row.id ?? ""),
    run_id: String(row.run_id ?? ""),
    signal_type: signalType,
    verdict,
    explanation: String(row.explanation ?? ""),
    evidence_event_ids: Array.isArray(evidence) ? evidence.map(String) : [],
    detector_version: String(row.detector_version ?? ""),
    created_at: (row.created_at as string | null) ?? null,
  };
}

export function toIssue(row: Record<string, unknown>): Issue {
  return {
    id: String(row.id ?? ""),
    title: (row.title as string | null) ?? null,
    description: (row.description as string | null) ?? null,
    created_at: (row.created_at as string | null) ?? null,
    raw: row,
  };
}

/** Keep the newest row when the same run and signal were classified more than once. */
export function latestSignals(signals: Signal[]): Signal[] {
  const seen = new Set<string>();
  const kept: Signal[] = [];
  const ordered = [...signals].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
  for (const signal of ordered) {
    const key = `${signal.run_id}:${signal.signal_type}`;
    if (seen.has(key)) continue;
    seen.add(key);
    kept.push(signal);
  }
  return kept;
}
