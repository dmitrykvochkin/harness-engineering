import { Brain, CircleX, Frown, type LucideIcon } from "lucide-react";

export const SIGNAL_TYPES = ["user_frustration", "task_failure", "forgetting"] as const;
export type SignalType = (typeof SIGNAL_TYPES)[number];

export const VERDICTS = ["present", "absent", "insufficient_evidence", "error"] as const;
export type Verdict = (typeof VERDICTS)[number];

export type SignalMeta = {
  type: SignalType;
  slug: string;
  label: string;
  short: string;
  description: string;
  icon: LucideIcon;
};

export const signalCatalog: SignalMeta[] = [
  {
    type: "user_frustration",
    slug: "user-frustration",
    label: "User Frustration",
    short: "Frustration",
    description:
      "The customer was unhappy with the agent or the conversation, even when the request was later sorted out.",
    icon: Frown,
  },
  {
    type: "task_failure",
    slug: "task-failure",
    label: "Task Failure",
    short: "Task",
    description:
      "A request the agent was allowed to do was done wrong, described as done when it was not, or left unfinished.",
    icon: CircleX,
  },
  {
    type: "forgetting",
    slug: "forgetting",
    label: "Forgetting",
    short: "Memory",
    description:
      "The agent later ignored something the customer had already said, such as an order number, address, or language.",
    icon: Brain,
  },
];

export const signalBySlug: Record<string, SignalMeta> = Object.fromEntries(
  signalCatalog.map((signal) => [signal.slug, signal]),
);

export const signalByType: Record<SignalType, SignalMeta> = Object.fromEntries(
  signalCatalog.map((signal) => [signal.type, signal]),
) as Record<SignalType, SignalMeta>;

export const verdictLabel: Record<Verdict, string> = {
  present: "Present",
  absent: "Clear",
  insufficient_evidence: "Unclear",
  error: "Error",
};

export function isSignalType(value: string): value is SignalType {
  return (SIGNAL_TYPES as readonly string[]).includes(value);
}

export function isVerdict(value: string): value is Verdict {
  return (VERDICTS as readonly string[]).includes(value);
}

export function modelLabel(detectorVersion: string): string {
  const withoutProvider = detectorVersion.includes(":")
    ? detectorVersion.slice(detectorVersion.indexOf(":") + 1)
    : detectorVersion;
  const slash = withoutProvider.lastIndexOf("/");
  return slash >= 0 ? withoutProvider.slice(slash + 1) : withoutProvider;
}

export function formatWhen(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatDuration(ms: number | null): string | null {
  if (ms == null || ms < 0) return null;
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}
