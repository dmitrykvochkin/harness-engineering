import { withSupabase } from "@supabase/server";

// Placeholder mapping until object models land — kind comes from the web nav
// (kebab-case), signal_type is the assumed column value.
const KIND_TO_TYPE: Record<string, string> = {
  negative: "negative",
  "tool-errors": "tool_errors",
};

export default {
  fetch: withSupabase({ auth: "publishable" }, async (req, ctx) => {
    const url = new URL(req.url);
    const kind = url.searchParams.get("kind");

    let query = ctx.supabase
      .from("signals")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(100);

    if (kind) {
      const signalType = KIND_TO_TYPE[kind];
      if (!signalType) {
        return Response.json({ error: `Unknown kind: ${kind}` }, { status: 400 });
      }
      query = query.eq("signal_type", signalType);
    }

    const { data, error } = await query;

    if (error) {
      return Response.json({ error: error.message }, { status: 500 });
    }

    return Response.json({ data });
  }),
};
