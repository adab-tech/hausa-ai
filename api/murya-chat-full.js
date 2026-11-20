const noCache = { "Cache-Control": "no-store" };

function error(status, message) {
  return Response.json({ error: message }, { status, headers: noCache });
}

export default {
  async fetch(request) {
    if (process.env.VITE_MURYA_CHAT_RELAY !== "1") return error(404, "Chat relay disabled");
    if (request.method !== "POST") {
      return new Response(null, { status: 405, headers: { ...noCache, Allow: "POST" } });
    }
    if (request.headers.get("origin") !== new URL(request.url).origin) {
      return error(403, "A same-origin request is required");
    }

    const origin = process.env.MURYA_RAILWAY_ORIGIN;
    const token = process.env.MURYA_RAILWAY_TOKEN;
    if (!origin || !token) return error(503, "Chat relay is unavailable");

    const payload = await request.text();
    if (Buffer.byteLength(payload, "utf8") > 256 * 1024) return error(413, "Chat request is too large");
    try {
      const body = JSON.parse(payload);
      if (typeof body?.text !== "string" || (body.attachments != null &&
        (!Array.isArray(body.attachments) || body.attachments.length > 0))) {
        return error(400, "A text-only chat request is required");
      }
    } catch {
      return error(400, "Invalid JSON");
    }

    try {
      const destination = new URL("/api/chat", origin);
      if (destination.protocol !== "https:") return error(503, "Chat relay is unavailable");

      const headers = new Headers({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" });
      const contributor = request.headers.get("x-contributor-id");
      if (contributor) headers.set("x-contributor-id", contributor);

      const upstream = await fetch(destination, {
        method: "POST",
        headers,
        body: payload,
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
      return error(502, "Chat relay is unavailable");
    }
  },
};
