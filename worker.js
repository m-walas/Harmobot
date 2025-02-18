export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/version") {
      const data = {
        version: env.WORKER_VERSION || "v0.0"
      };
      return new Response(JSON.stringify(data), {
        headers: { "Content-Type": "application/json" }
      });
    }
    return new Response("404 Not Found", { status: 404 });
  }
};
