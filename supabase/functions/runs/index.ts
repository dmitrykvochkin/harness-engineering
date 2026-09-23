import { withSupabase } from "@supabase/server";

export default {
  fetch: withSupabase({ auth: "publishable" }, async (req, ctx) => {
    const runId = new URL(req.url).searchParams.get("run_id");
    if (!runId) {
      return Response.json({ error: "run_id is required" }, { status: 400 });
    }

    const [runRes, eventsRes, signalsRes] = await Promise.all([
      ctx.supabase
        .from("runs")
        .select("run_id, agent_version, start_time, duration_ms, environment")
        .eq("run_id", runId)
        .maybeSingle(),
      ctx.supabase
        .from("events")
        .select("id, seq, type, role, content, tool_name, status, timestamp")
        .eq("run_id", runId)
        .order("seq", { ascending: true }),
      ctx.supabase
        .from("signals")
        .select(
          "id, run_id, signal_type, verdict, explanation, evidence_event_ids, detector_version, created_at",
        )
        .eq("run_id", runId)
        .order("created_at", { ascending: false }),
    ]);

    const error = runRes.error ?? eventsRes.error ?? signalsRes.error;
    if (error) {
      return Response.json({ error: error.message }, { status: 500 });
    }
    if (!runRes.data) {
      return Response.json({ error: "Run not found" }, { status: 404 });
    }

    return Response.json({
      run: runRes.data,
      events: eventsRes.data ?? [],
      signals: signalsRes.data ?? [],
    });
  }),
};
