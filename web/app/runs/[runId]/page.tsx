import Link from "next/link";
import { notFound } from "next/navigation";

import { ConversationTimeline } from "@/components/conversation-timeline";
import { NavPageHeader } from "@/components/nav-page-header";
import { VerdictBadge } from "@/components/verdict-badge";
import { getRun } from "@/lib/data";
import { signalsInOrder } from "@/lib/group";
import { formatDuration, formatWhen, modelLabel, signalByType, type SignalType } from "@/lib/signals";

export const dynamic = "force-dynamic";

export default async function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;

  let detail;
  try {
    detail = await getRun(runId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "";
    if (message.toLowerCase().includes("not found")) notFound();
    return (
      <div className="flex flex-1 flex-col gap-6 p-6">
        <NavPageHeader title={runId} description="Conversation and detector findings." />
        <p className="text-sm text-muted-foreground">{message || "Could not load this run."}</p>
      </div>
    );
  }

  const findings = signalsInOrder(detail.signals);
  const model = findings[0] ? modelLabel(findings[0].detector_version) : null;
  const when = formatWhen(detail.run.start_time);
  const duration = formatDuration(detail.run.duration_ms);
  const meta = [model, when, duration].filter(Boolean).join(" · ");

  const citedByEvent = new Map<string, SignalType[]>();
  for (const finding of findings) {
    for (const eventId of finding.evidence_event_ids) {
      const current = citedByEvent.get(eventId) ?? [];
      current.push(finding.signal_type);
      citedByEvent.set(eventId, current);
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <Link href="/signals" className="text-sm text-muted-foreground hover:text-foreground">
          All signals
        </Link>
        <NavPageHeader title={detail.run.run_id} description={meta || "Conversation and detector findings."} />
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="flex flex-col gap-3">
          {findings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No detector results for this run yet.</p>
          ) : (
            findings.map((finding) => {
              const info = signalByType[finding.signal_type];
              return (
                <section key={finding.signal_type} className="rounded-xl border bg-card p-4">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-sm font-medium">{info.label}</h2>
                    <VerdictBadge verdict={finding.verdict} />
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{finding.explanation}</p>
                  {finding.evidence_event_ids.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {finding.evidence_event_ids.map((eventId) => (
                        <a
                          key={eventId}
                          href={`#${eventId}`}
                          className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground hover:text-foreground"
                        >
                          {eventId}
                        </a>
                      ))}
                    </div>
                  )}
                </section>
              );
            })
          )}
        </aside>
        <ConversationTimeline events={detail.events} citedByEvent={citedByEvent} />
      </div>
    </div>
  );
}
