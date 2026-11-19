const headers = { "Cache-Control": "no-store" };
const maxTextLength = 300;

function error(status, message) {
  return Response.json({ error: message }, { status, headers });
}

export default {
  async fetch(request) {
    if (request.method !== "POST") {
      return new Response(null, { status: 405, headers: { ...headers, Allow: "POST" } });
    }
    const origin = request.headers.get("origin");
    if (origin && origin !== new URL(request.url).origin) {
      return error(403, "Cross-origin requests are not supported");
    }

    const body = await request.json().catch(() => null);
    const text = typeof body?.text === "string" ? body.text.trim() : "";
    if (!text || text.length > maxTextLength) {
      return error(400, "Supply between 1 and 300 characters");
    }

    const endpoint = process.env.MURYA_VOICE_ENDPOINT;
    const token = process.env.MURYA_VOICE_PREVIEW_TOKEN;
    if (!endpoint || !token) return error(503, "Voice service unavailable");

    try {
      const upstream = await fetch(endpoint, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
        redirect: "error",
        signal: AbortSignal.timeout(25000),
      });
      if (upstream.status === 429 || upstream.status === 503) {
        return new Response(null, { status: 503, headers: { ...headers, "Retry-After": "1" } });
      }
      if (!upstream.ok || !upstream.body || upstream.headers.get("content-type") !== "audio/wav") {
        return error(502, "Voice service could not synthesize audio");
      }
      return new Response(upstream.body, { headers: { ...headers, "Content-Type": "audio/wav" } });
    } catch {
      return error(502, "Voice service unavailable");
    }
  },
};
