import { withSupabase } from "@supabase/server";

const SIGNAL_TYPES = ["user_frustration", "task_failure", "forgetting"];
const VERDICTS = ["present", "absent", "insufficient_evidence", "error"];

export default {
  fetch: withSupabase({ auth: "publishable" }, async (req, ctx) => {
    const url = new URL(req.url);
    const signalType = url.searchParams.get("signal_type");
    const verdict = url.searchParams.get("verdict");

    if (signalType && !SIGNAL_TYPES.includes(signalType)) {
      return Response.json({ error: `Unknown signal_type: ${signalType}` }, { status: 400 });
    }
    if (verdict && !VERDICTS.includes(verdict)) {
      return Response.json({ error: `Unknown verdict: ${verdict}` }, { status: 400 });
    }

    let query = ctx.supabase
      .from("signals")
      .select(
        "id, run_id, signal_type, verdict, explanation, evidence_event_ids, detector_version, created_at",
      )
      .order("created_at", { ascending: false })
      .limit(1000);

    if (signalType) query = query.eq("signal_type", signalType);
    if (verdict) query = query.eq("verdict", verdict);

    const { data, error } = await query;
    if (error) {
      return Response.json({ error: error.message }, { status: 500 });
    }
    return Response.json({ data });
  }),
};
