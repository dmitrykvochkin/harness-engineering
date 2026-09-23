import { withSupabase } from "@supabase/server";

export default {
  fetch: withSupabase({ auth: "publishable" }, async (_req, ctx) => {
    const { data, error } = await ctx.supabase
      .from("issues")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(100);

    if (error) {
      return Response.json({ error: error.message }, { status: 500 });
    }

    return Response.json({ data });
  }),
};
