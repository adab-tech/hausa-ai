const noCache = { "Cache-Control": "no-store" };

function error(status, message) {
  return Response.json({ error: message }, { status, headers: noCache });
}

export default {
  async fetch(request) {
    if (process.env.VERCEL_ENV !== "preview") return error(404, "Preview route");
    if (request.method !== "POST") {
      return new Response(null, { status: 405, headers: { ...noCache, Allow: "POST" } });
    }
    if (request.headers.get("origin") !== new URL(request.url).origin) {
      return error(403, "A same-origin request is required");
    }

    const endpoint = process.env.MURYA_VOICE_ENDPOINT;
    const token = process.env.MURYA_VOICE_PREVIEW_TOKEN;
    if (!endpoint || !token) return error(503, "Preview chat is unavailable");

    try {
      const destination = new URL("/api/chat", endpoint);
      if (destination.protocol !== "https:") return error(503, "Preview chat is unavailable");

      const headers = new Headers({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" });
      const contributor = request.headers.get("x-contributor-id");
      if (contributor) headers.set("x-contributor-id", contributor);

      const upstream = await fetch(destination, {
        method: "POST",
        headers,
        body: await request.arrayBuffer(),
        redirect: "error",
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(55000)]),
      });

      const responseHeaders = new Headers(noCache);
      for (const name of ["content-type", "retry-after"]) {
        const value = upstream.headers.get(name);
        if (value) responseHeaders.set(name, value);
      }
      return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
    } catch {
      return error(502, "Preview chat is unavailable");
    }
  },
};
