import Link from "next/link";

import { NavPageHeader } from "@/components/nav-page-header";
import { VerdictBadge } from "@/components/verdict-badge";
import { getSignals } from "@/lib/data";
import { countVerdicts, groupByRun } from "@/lib/group";
import { modelLabel, signalCatalog } from "@/lib/signals";

export const dynamic = "force-dynamic";

function LoadError({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed px-4 py-8 text-sm text-muted-foreground">
      <p>Detector results are not available yet.</p>
      <p className="mt-2">{message}</p>
    </div>
  );
}

export default async function SignalsPage() {
  let signals;
  try {
    signals = await getSignals();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load signals";
    return (
      <div className="flex flex-1 flex-col gap-6 p-6">
        <NavPageHeader
          title="Signals"
          description="What the detectors found in each conversation."
        />
        <LoadError message={message} />
      </div>
    );
  }

  const groups = groupByRun(signals);
  const runCount = groups.length;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader
        title="Signals"
        description={
          runCount === 0
            ? "What the detectors found in each conversation."
            : `What the detectors found across ${runCount} conversations.`
        }
      />

      {runCount === 0 ? (
        <div className="rounded-xl border border-dashed px-4 py-8 text-sm text-muted-foreground">
          No detector results yet. From the <span className="font-medium text-foreground">ai</span>{" "}
          folder, run <span className="font-mono">uv run harness-upload-results</span>.
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            {signalCatalog.map((meta) => {
              const counts = countVerdicts(signals.filter((signal) => signal.signal_type === meta.type));
              return (
                <Link
                  key={meta.type}
                  href={`/signals/${meta.slug}`}
                  className="rounded-xl border bg-card p-4 transition-colors hover:bg-accent/40"
                >
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <meta.icon className="size-4 text-muted-foreground" />
                    {meta.label}
                  </div>
                  <p className="mt-3 text-3xl font-semibold tracking-tight">{counts.present}</p>
                  <p className="text-sm text-muted-foreground">present</p>
                  <p className="mt-3 text-xs text-muted-foreground">
                    {counts.insufficient_evidence} unclear · {counts.absent} clear
                    {counts.error > 0
                      ? ` · ${counts.error} ${counts.error === 1 ? "error" : "errors"}`
                      : ""}
                  </p>
                </Link>
              );
            })}
          </div>

          <div className="overflow-hidden rounded-xl border">
            <div className="grid grid-cols-[7.5rem_minmax(0,1.4fr)_repeat(3,minmax(5.5rem,1fr))] bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground">
              <span>Run</span>
              <span>Model</span>
              {signalCatalog.map((meta) => (
                <span key={meta.type}>{meta.short}</span>
              ))}
            </div>
            {groups.map((group) => (
              <Link
                key={group.runId}
                href={`/runs/${group.runId}`}
                className="grid grid-cols-[7.5rem_minmax(0,1.4fr)_repeat(3,minmax(5.5rem,1fr))] items-center border-t px-4 py-3 text-sm hover:bg-muted/30"
              >
                <span className="font-medium">{group.runId}</span>
                <span className="truncate text-muted-foreground">{modelLabel(group.model)}</span>
                {signalCatalog.map((meta) => {
                  const finding = group.byType[meta.type];
                  return (
                    <span key={meta.type}>
                      {finding ? <VerdictBadge verdict={finding.verdict} /> : "—"}
                    </span>
                  );
                })}
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
