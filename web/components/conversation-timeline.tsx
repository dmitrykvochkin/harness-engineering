import { cn } from "cn";

import { signalByType, type SignalType } from "@/lib/signals";
import type { TraceEvent } from "@/lib/types";

function summarize(content: string): string {
  const trimmed = content.trim();
  if (!trimmed) return "";
  try {
    const value = JSON.parse(trimmed) as unknown;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return Object.entries(value as Record<string, unknown>)
        .slice(0, 6)
        .map(([key, item]) => `${key}: ${typeof item === "string" ? item : JSON.stringify(item)}`)
        .join(" · ");
    }
  } catch {
    // Plain text.
  }
  return trimmed.length > 280 ? `${trimmed.slice(0, 280)}…` : trimmed;
}

function citedLabel(types: SignalType[]): string {
  return types.map((type) => signalByType[type].short).join(", ");
}

export function ConversationTimeline({
  events,
  citedByEvent,
}: {
  events: TraceEvent[];
  citedByEvent: Map<string, SignalType[]>;
}) {
  const system = events.filter((event) => event.type === "system_message");
  const visible = events.filter(
    (event) => event.type !== "system_message" && !(event.type === "generation" && !event.content.trim()),
  );

  return (
    <div className="flex flex-col gap-3">
      {system.length > 0 && (
        <details className="rounded-lg border bg-card px-4 py-3 text-sm">
          <summary className="cursor-pointer text-muted-foreground">
            System prompt ({system.length})
          </summary>
          <div className="mt-3 flex flex-col gap-2">
            {system.map((event) => (
              <p key={event.id} className="whitespace-pre-wrap text-muted-foreground">
                {event.content}
              </p>
            ))}
          </div>
        </details>
      )}
      {visible.map((event) => {
        const cited = citedByEvent.get(event.id) ?? [];
        const highlighted = cited.length > 0;
        if (event.type === "user_message" || event.type === "generation") {
          const fromCustomer = event.type === "user_message";
          return (
            <div
              key={event.id}
              id={event.id}
              className={cn("flex scroll-mt-20", fromCustomer ? "justify-end" : "justify-start")}
            >
              <div
                className={cn(
                  "max-w-[40rem] rounded-2xl px-4 py-3",
                  fromCustomer ? "bg-primary text-primary-foreground" : "border bg-card",
                  highlighted && "ring-2 ring-amber-400/80",
                )}
              >
                <div className="mb-1 flex items-center gap-2 text-xs opacity-70">
                  <span>{fromCustomer ? "Customer" : "Agent"}</span>
                  {highlighted && <span>Cited · {citedLabel(cited)}</span>}
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{event.content}</p>
              </div>
            </div>
          );
        }

        const label =
          event.type === "tool_result"
            ? `Result${event.tool_name ? ` · ${event.tool_name}` : ""}${event.status ? ` · ${event.status}` : ""}`
            : `Called ${event.tool_name ?? event.type}`;
        return (
          <div
            key={event.id}
            id={event.id}
            className={cn(
              "scroll-mt-20 rounded-lg border border-dashed px-3 py-2 text-xs",
              highlighted ? "border-amber-400/80 bg-amber-400/10" : "text-muted-foreground",
            )}
          >
            <div className="font-medium text-foreground">
              {label}
              {highlighted && <span className="ml-2 font-normal text-amber-700 dark:text-amber-200">Cited · {citedLabel(cited)}</span>}
            </div>
            {summarize(event.content) && (
              <p className="mt-1 leading-relaxed">{summarize(event.content)}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
