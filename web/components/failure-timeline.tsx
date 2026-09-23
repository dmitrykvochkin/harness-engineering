"use client";

import Link from "next/link";
import { useState } from "react";

import type { FailureTimeline } from "@/lib/failure-timeline";
import { signalByType, signalCatalog, type SignalType } from "@/lib/signals";

const signalColor: Record<SignalType, string> = {
  user_frustration: "oklch(0.84 0.15 85)",
  task_failure: "oklch(0.7 0.19 25)",
  forgetting: "oklch(0.75 0.13 255)",
};

const W = 760;
const H = 210;
const PAD_X = 8;
const STRIP_TOP = 4;
const STRIP_H = 78;
const BARS_TOP = 96;
const BARS_H = 78;
const HOUR_MS = 3_600_000;

const dayFormat = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

const hourFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "UTC",
});

function countMarks(timeline: FailureTimeline, type: SignalType): number {
  return timeline.marks.filter((mark) => mark.signalType === type).length;
}

function xFor(time: number, timeline: FailureTimeline): number {
  const span = timeline.domainEnd - timeline.domainStart;
  const inner = W - PAD_X * 2;
  return PAD_X + ((time - timeline.domainStart) / span) * inner;
}

function laneY(type: SignalType): number {
  const index = signalCatalog.findIndex((meta) => meta.type === type);
  return STRIP_TOP + ((index + 0.5) / signalCatalog.length) * STRIP_H;
}

function jitter(key: string): number {
  let hash = 2166136261;
  for (let index = 0; index < key.length; index += 1) {
    hash ^= key.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 2 ** 32;
}

function smoothLine(points: { x: number; y: number }[], top: number, bottom: number): string {
  const first = points[0];
  if (!first) return "";
  const clamp = (y: number) => Math.max(top, Math.min(bottom, y));
  let path = `M${first.x.toFixed(2)} ${first.y.toFixed(2)}`;
  for (let index = 0; index < points.length - 1; index += 1) {
    const p0 = points[index - 1] ?? points[index];
    const p1 = points[index];
    const p2 = points[index + 1];
    const p3 = points[index + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = clamp(p1.y + (p2.y - p0.y) / 6);
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = clamp(p2.y - (p3.y - p1.y) / 6);
    path += ` C${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }
  return path;
}

function dayTicks(timeline: FailureTimeline): number[] {
  const ticks = [timeline.domainStart];
  const cursor = new Date(timeline.domainStart);
  cursor.setUTCHours(0, 0, 0, 0);
  cursor.setUTCDate(cursor.getUTCDate() + 1);
  while (cursor.getTime() < timeline.domainEnd) {
    ticks.push(cursor.getTime());
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return ticks;
}

export function FailureTimelineChart({ timeline }: { timeline: FailureTimeline }) {
  const [active, setActive] = useState<number | null>(null);
  const baseline = BARS_TOP + BARS_H;
  const maxRequests = Math.max(...timeline.buckets.map((bucket) => bucket.requests), 1);
  const points = [
    {
      x: xFor(timeline.domainStart, timeline),
      y: BARS_TOP + (1 - (timeline.buckets[0]?.requests ?? 0) / maxRequests) * BARS_H,
    },
    ...timeline.buckets.map((bucket) => ({
      x: xFor(bucket.start + HOUR_MS / 2, timeline),
      y: BARS_TOP + (1 - bucket.requests / maxRequests) * BARS_H,
    })),
    {
      x: xFor(timeline.domainEnd, timeline),
      y: BARS_TOP + (1 - (timeline.buckets.at(-1)?.requests ?? 0) / maxRequests) * BARS_H,
    },
  ];
  const volumeLine = smoothLine(points, BARS_TOP, baseline);
  const firstPoint = points[0];
  const lastPoint = points[points.length - 1];
  const volumeArea =
    firstPoint && lastPoint
      ? `${volumeLine} L${lastPoint.x.toFixed(2)} ${baseline.toFixed(2)} L${firstPoint.x.toFixed(2)} ${baseline.toFixed(2)} Z`
      : "";
  const activeBucket = active == null ? null : timeline.buckets[active];
  const activeMarks =
    activeBucket == null
      ? []
      : timeline.marks.filter(
          (mark) => mark.at >= activeBucket.start && mark.at < activeBucket.start + HOUR_MS,
        );
  const detectedRuns = new Set(timeline.marks.map((mark) => mark.runId)).size;

  function bucketAt(clientX: number, width: number): number {
    const x = (clientX / width) * W;
    const inner = W - PAD_X * 2;
    const ratio = (x - PAD_X) / inner;
    const index = Math.floor(ratio * timeline.buckets.length);
    return Math.max(0, Math.min(timeline.buckets.length - 1, index));
  }

  return (
    <section className="rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <h2 className="text-sm font-medium">Detected in traffic</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {timeline.assumedRequests.toLocaleString("en-GB")} requests assumed for this window.
            Marks are the frustrations, task failures, and memory gaps the detectors found.
          </p>
        </div>
        <div className="flex gap-6">
          <div>
            <div className="text-2xl font-semibold tracking-tight tabular-nums">
              {timeline.assumedRequests.toLocaleString("en-GB")}
            </div>
            <div className="text-xs text-muted-foreground">requests</div>
          </div>
          <div>
            <div className="text-2xl font-semibold tracking-tight tabular-nums">
              {timeline.marks.length}
            </div>
            <div className="text-xs text-muted-foreground">
              detected · {detectedRuns} {detectedRuns === 1 ? "conversation" : "conversations"}
            </div>
          </div>
        </div>
      </div>

      <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {signalCatalog.map((meta) => (
          <li key={meta.type} className="flex items-center gap-1.5">
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: signalColor[meta.type] }}
            />
            {meta.short}
            <span className="tabular-nums text-foreground">{countMarks(timeline, meta.type)}</span>
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm bg-foreground/20" />
          Requests
        </li>
      </ul>

      <div
        className="relative mt-3"
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          setActive(bucketAt(event.clientX - rect.left, rect.width));
        }}
        onMouseLeave={() => setActive(null)}
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block h-auto w-full"
          role="img"
          aria-label={`${timeline.assumedRequests.toLocaleString("en-GB")} assumed requests, ${timeline.marks.length} signals detected`}
        >
          {signalCatalog.map((meta) => (
            <line
              key={meta.type}
              x1={PAD_X}
              x2={W - PAD_X}
              y1={laneY(meta.type)}
              y2={laneY(meta.type)}
              stroke="currentColor"
              strokeOpacity={0.08}
            />
          ))}

          <path d={volumeArea} fill="currentColor" fillOpacity={0.12} />
          <path d={volumeLine} fill="none" stroke="currentColor" strokeOpacity={0.45} strokeWidth={1.5} />

          {activeBucket && (
            <line
              x1={xFor(activeBucket.start + HOUR_MS / 2, timeline)}
              x2={xFor(activeBucket.start + HOUR_MS / 2, timeline)}
              y1={STRIP_TOP}
              y2={baseline}
              stroke="currentColor"
              strokeOpacity={0.35}
              strokeDasharray="3 3"
            />
          )}

          {dayTicks(timeline).map((tick, index) => (
            <text
              key={tick}
              x={Math.max(PAD_X, xFor(tick, timeline))}
              y={H - 8}
              fill="currentColor"
              fillOpacity={0.55}
              fontSize={11}
              textAnchor={index === 0 ? "start" : "middle"}
            >
              {dayFormat.format(tick)}
            </text>
          ))}
          <text
            x={W - PAD_X}
            y={H - 8}
            fill="currentColor"
            fillOpacity={0.4}
            fontSize={11}
            textAnchor="end"
          >
            UTC
          </text>
        </svg>

        <div className="absolute inset-0">
          {timeline.marks.map((mark) => {
            const hour = Math.floor((mark.at - timeline.domainStart) / HOUR_MS);
            const highlighted = active == null || hour === active;
            const spread = jitter(`${mark.runId}:${mark.signalType}`);
            const barWidth = (W - PAD_X * 2) / timeline.buckets.length;
            const cx = Math.min(
              W - PAD_X,
              Math.max(PAD_X, xFor(mark.at, timeline) + (spread - 0.5) * barWidth * 0.45),
            );
            const cy = laneY(mark.signalType) + (jitter(`${mark.signalType}:${mark.runId}`) - 0.5) * 8;
            const label = signalByType[mark.signalType].label;
            return (
              <Link
                key={`${mark.runId}:${mark.signalType}`}
                href={`/runs/${mark.runId}`}
                title={`${label} · ${mark.runId}`}
                aria-label={`${label}, ${mark.runId}`}
                className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
                style={{
                  left: `${(cx / W) * 100}%`,
                  top: `${(cy / H) * 100}%`,
                  width: highlighted && active != null ? 10 : 8,
                  height: highlighted && active != null ? 10 : 8,
                  backgroundColor: signalColor[mark.signalType],
                  opacity: highlighted ? 1 : 0.28,
                }}
              />
            );
          })}
        </div>

        {activeBucket && (
          <div
            className="pointer-events-none absolute top-0 z-10 w-52 rounded-lg border bg-popover px-3 py-2 text-xs shadow-md"
            style={{
              left: `clamp(0px, calc(${(xFor(activeBucket.start + HOUR_MS / 2, timeline) / W) * 100}% - 6.5rem), calc(100% - 13rem))`,
            }}
          >
            <p className="font-medium text-foreground">
              {hourFormat.format(activeBucket.start)} UTC
            </p>
            <p className="mt-1 text-muted-foreground">
              {activeBucket.requests.toLocaleString("en-GB")} requests
            </p>
            {activeMarks.length === 0 ? (
              <p className="mt-1 text-muted-foreground">Nothing detected</p>
            ) : (
              <ul className="mt-1.5 flex flex-col gap-1">
                {activeMarks.slice(0, 4).map((mark) => (
                  <li key={`${mark.runId}:${mark.signalType}`} className="flex items-center gap-1.5">
                    <span
                      className="size-1.5 shrink-0 rounded-full"
                      style={{ backgroundColor: signalColor[mark.signalType] }}
                    />
                    <span className="text-foreground">{signalByType[mark.signalType].short}</span>
                    <span className="truncate text-muted-foreground">{mark.runId}</span>
                  </li>
                ))}
                {activeMarks.length > 4 && (
                  <li className="text-muted-foreground">+{activeMarks.length - 4} more</li>
                )}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
