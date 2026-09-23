import type { SignalType } from "./signals";
import type { Signal } from "./types";

/**
 * Assumed support-chat volume across the window these conversations span.
 * About 50 requests an hour on average: near 100 in the early afternoon UTC
 * (mid-afternoon in Europe) and about 20 overnight.
 */
export const ASSUMED_REQUESTS = 2400;

const HOUR_MS = 3_600_000;
const PEAK_HOUR_UTC = 12;

export type TimelineMark = {
  runId: string;
  signalType: SignalType;
  at: number;
};

export type TimelineBucket = {
  start: number;
  requests: number;
};

export type FailureTimeline = {
  assumedRequests: number;
  domainStart: number;
  domainEnd: number;
  buckets: TimelineBucket[];
  marks: TimelineMark[];
};

export function buildFailureTimeline(
  signals: Signal[],
  runStarts: readonly { runId: string; startTime: string }[],
): FailureTimeline | null {
  const startByRun = new Map(runStarts.map((run) => [run.runId, Date.parse(run.startTime)]));
  const runTimes = [...startByRun.values()].filter((time) => !Number.isNaN(time));
  if (runTimes.length === 0) return null;

  const domainStart = startOfUtcHour(Math.min(...runTimes));
  const domainEnd = startOfUtcHour(Math.max(...runTimes)) + HOUR_MS;

  const buckets: TimelineBucket[] = [];
  for (let start = domainStart; start < domainEnd; start += HOUR_MS) {
    buckets.push({ start, requests: 0 });
  }

  const weights = buckets.map((bucket) => diurnalWeight(new Date(bucket.start).getUTCHours()));
  const requests = distribute(weights, ASSUMED_REQUESTS);
  for (let index = 0; index < buckets.length; index += 1) {
    buckets[index].requests = requests[index] ?? 0;
  }

  const marks: TimelineMark[] = [];
  for (const signal of signals) {
    if (signal.verdict !== "present") continue;
    const at = startByRun.get(signal.run_id);
    if (at == null || Number.isNaN(at)) continue;
    marks.push({ runId: signal.run_id, signalType: signal.signal_type, at });
  }
  marks.sort((a, b) => a.at - b.at || a.runId.localeCompare(b.runId) || a.signalType.localeCompare(b.signalType));

  return {
    assumedRequests: ASSUMED_REQUESTS,
    domainStart,
    domainEnd,
    buckets,
    marks,
  };
}

function startOfUtcHour(ms: number): number {
  const date = new Date(ms);
  date.setUTCMinutes(0, 0, 0);
  return date.getTime();
}

/** Higher around early afternoon UTC, with a floor so nights are quiet rather than empty. */
function diurnalWeight(hourUtc: number): number {
  const delta = Math.min(Math.abs(hourUtc - PEAK_HOUR_UTC), 24 - Math.abs(hourUtc - PEAK_HOUR_UTC));
  return 0.22 + 0.78 * Math.exp(-(delta * delta) / 28);
}

function distribute(weights: number[], total: number): number[] {
  const weightSum = weights.reduce((sum, weight) => sum + weight, 0);
  const exact = weights.map((weight) => (weightSum === 0 ? 0 : (weight / weightSum) * total));
  const counts = exact.map((value) => Math.floor(value));
  let remaining = total - counts.reduce((sum, count) => sum + count, 0);
  const ranked = exact
    .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
    .sort((a, b) => b.fraction - a.fraction || a.index - b.index);
  for (const item of ranked) {
    if (remaining <= 0) break;
    counts[item.index] += 1;
    remaining -= 1;
  }
  return counts;
}
