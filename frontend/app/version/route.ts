export const dynamic = "force-static";

/** The commit and time this build was made from, to tell a stale deploy from a fresh one. */
export function GET() {
  return Response.json(
    { commit: process.env.BUILD_COMMIT, builtAt: process.env.BUILD_TIME },
    { headers: { "Cache-Control": "no-store" } },
  );
}
