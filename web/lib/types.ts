// Placeholder types — replace when the object models are designed.
// Field names assume snake_case columns in the public schema.
// `unknown` marks fields we render but whose exact shape is TBD.

export type Signal = {
  id: string;
  run_id: string | null;
  signal_type: string | null;
  created_at: string | null;
  raw: Record<string, unknown>;
};

export type Issue = {
  id: string;
  title: string | null;
  description: string | null;
  created_at: string | null;
  raw: Record<string, unknown>;
};

// Map a row to the loose view type; keeps one place to adjust when the
// real schema lands.
export function toSignal(row: Record<string, unknown>): Signal {
  return {
    id: String(row.id ?? ""),
    run_id: (row.run_id as string | null) ?? null,
    signal_type: (row.signal_type as string | null) ?? null,
    created_at: (row.created_at as string | null) ?? null,
    raw: row,
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
