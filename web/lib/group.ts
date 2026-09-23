import { signalCatalog, type SignalType, type Verdict } from "./signals";
import type { Signal } from "./types";

export type RunGroup = {
  runId: string;
  model: string;
  byType: Partial<Record<SignalType, Signal>>;
};

export function countVerdicts(signals: Signal[]): Record<Verdict, number> {
  const counts: Record<Verdict, number> = {
    present: 0,
    absent: 0,
    insufficient_evidence: 0,
    error: 0,
  };
  for (const signal of signals) counts[signal.verdict] += 1;
  return counts;
}

export function groupByRun(signals: Signal[]): RunGroup[] {
  const groups = new Map<string, RunGroup>();
  for (const signal of signals) {
    let group = groups.get(signal.run_id);
    if (!group) {
      group = { runId: signal.run_id, model: signal.detector_version, byType: {} };
      groups.set(signal.run_id, group);
    }
    group.byType[signal.signal_type] = signal;
    if (signal.detector_version) group.model = signal.detector_version;
  }
  return [...groups.values()].sort((a, b) =>
    a.runId.localeCompare(b.runId, undefined, { numeric: true }),
  );
}

export function signalsInOrder(signals: Signal[]): Signal[] {
  return signalCatalog.map((meta) => signals.find((signal) => signal.signal_type === meta.type)).filter(
    (signal): signal is Signal => signal !== undefined,
  );
}
