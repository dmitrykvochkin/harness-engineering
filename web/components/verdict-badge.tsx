import { cn } from "cn";

import { verdictLabel, type Verdict } from "@/lib/signals";

const verdictClass: Record<Verdict, string> = {
  present: "border-transparent bg-red-500/15 text-red-700 dark:text-red-300",
  absent: "border-transparent bg-emerald-500/15 text-emerald-800 dark:text-emerald-300",
  insufficient_evidence: "border-transparent bg-amber-500/15 text-amber-800 dark:text-amber-200",
  error: "border-transparent bg-muted text-muted-foreground",
};

export function VerdictBadge({
  verdict,
  className,
}: {
  verdict: Verdict;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full px-2 text-xs font-medium whitespace-nowrap",
        verdictClass[verdict],
        className,
      )}
    >
      {verdictLabel[verdict]}
    </span>
  );
}
