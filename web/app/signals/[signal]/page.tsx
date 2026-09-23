import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteSignalButton } from "@/components/delete-signal-button";
import { NavPageHeader } from "@/components/nav-page-header";
import { VerdictBadge } from "@/components/verdict-badge";
import { getSignalDefinition, getSignals } from "@/lib/data";
import { countVerdicts } from "@/lib/group";
import { isVerdict, modelLabel, signalBySlug, verdictLabel, type Verdict } from "@/lib/signals";
import { cn } from "cn";

export const dynamic = "force-dynamic";

const FILTERS: { verdict: Verdict | "all"; label: string }[] = [
  { verdict: "present", label: "Present" },
  { verdict: "insufficient_evidence", label: "Unclear" },
  { verdict: "absent", label: "Clear" },
  { verdict: "error", label: "Errors" },
  { verdict: "all", label: "All" },
];

export default async function SignalTypePage({
  params,
  searchParams,
}: {
  params: Promise<{ signal: string }>;
  searchParams: Promise<{ verdict?: string }>;
}) {
  const { signal: slug } = await params;
  const meta = signalBySlug[slug];
  if (!meta) return <DefinedSignalPage slug={slug} />;

  const { verdict: requested } = await searchParams;
  const selected: Verdict | "all" =
    requested === "all" || (requested !== undefined && isVerdict(requested)) ? requested : "present";

  let signals;
  try {
    signals = (await getSignals()).filter((row) => row.signal_type === meta.type);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load signals";
    return (
      <div className="flex flex-1 flex-col gap-6 p-6">
        <NavPageHeader title={meta.label} description={meta.description} />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    );
  }

  const counts = countVerdicts(signals);
  const visible =
    selected === "all" ? signals : signals.filter((row) => row.verdict === selected);
  visible.sort((a, b) => a.run_id.localeCompare(b.run_id, undefined, { numeric: true }));

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader title={meta.label} description={meta.description} />

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => {
          const count = filter.verdict === "all" ? signals.length : counts[filter.verdict];
          const active = filter.verdict === selected;
          const href =
            filter.verdict === "present"
              ? `/signals/${meta.slug}`
              : `/signals/${meta.slug}?verdict=${filter.verdict}`;
          return (
            <Link
              key={filter.verdict}
              href={href}
              className={cn(
                "rounded-full border px-3 py-1 text-sm",
                active ? "border-foreground bg-foreground text-background" : "text-muted-foreground hover:bg-muted",
              )}
            >
              {filter.label}
              <span className="ml-1.5 tabular-nums">{count}</span>
            </Link>
          );
        })}
      </div>

      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {selected === "all"
            ? "Nothing classified for this signal yet."
            : `No conversations marked ${verdictLabel[selected].toLowerCase()}. Try another filter.`}
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {visible.map((signal) => (
            <Link
              key={signal.id || `${signal.run_id}:${signal.signal_type}`}
              href={`/runs/${signal.run_id}`}
              className="rounded-xl border bg-card p-4 transition-colors hover:bg-accent/40"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{signal.run_id}</p>
                  <p className="text-xs text-muted-foreground">{modelLabel(signal.detector_version)}</p>
                </div>
                <VerdictBadge verdict={signal.verdict} />
              </div>
              <p className="mt-3 text-sm leading-relaxed">{signal.explanation}</p>
              {signal.evidence_event_ids.length > 0 && (
                <p className="mt-3 font-mono text-xs text-muted-foreground">
                  {signal.evidence_event_ids.join("  ")}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

async function DefinedSignalPage({ slug }: { slug: string }) {
  let definition;
  try {
    definition = await getSignalDefinition(slug);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load this signal";
    return (
      <div className="flex flex-1 flex-col gap-6 p-6">
        <NavPageHeader title="Signal" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    );
  }

  if (!definition) notFound();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <NavPageHeader
        title={definition.title}
        description="Saved signal. Evaluation runs separately."
        action={<DeleteSignalButton slug={definition.slug} />}
      />
      <div className="rounded-xl border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">Prompt</p>
        <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">{definition.prompt}</p>
      </div>
      <p className="text-sm text-muted-foreground">No evaluations yet.</p>
    </div>
  );
}
