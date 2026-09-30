export const dynamic = "force-dynamic";

/**
 * The commit this build was made from (`commit`, fixed at build time) next to the commit Render
 * says is running (`runningCommit`). They differ when a deploy serves a stale build.
 */
export function GET() {
  return Response.json(
    {
      commit: process.env.BUILD_COMMIT,
      builtAt: process.env.BUILD_TIME,
      runningCommit: process.env.RENDER_GIT_COMMIT ?? null,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
