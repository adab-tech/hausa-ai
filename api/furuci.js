const routes = {
  GET: [/^admin\/(?:me|audit-log|pronunciation(?:\/(?:counts|export|[0-9]+\/audio))?)$/],
  POST: [/^pronunciation\/(?:flag|submit)$/, /^admin\/(?:login|logout|change-password|pronunciation(?:\/[0-9]+\/(?:record|status))?)$/],
  DELETE: [/^admin\/pronunciation\/[0-9]+$/],
};

function error(status, message) {
  return Response.json({ error: message }, { status, headers: { "Cache-Control": "no-store" } });
}

export default {
  async fetch(request) {
    if (process.env.VERCEL_ENV !== "preview") return error(404, "Preview route");
    const url = new URL(request.url);
    const route = url.searchParams.get("route") ?? "";
    if (!routes[request.method]?.some((pattern) => pattern.test(route))) {
      return error(404, "Unknown pronunciation route");
    }
    if (request.method !== "GET" && request.headers.get("origin") !== url.origin) {
      return error(403, "A same-origin request is required");
    }

    const endpoint = process.env.MURYA_VOICE_ENDPOINT;
    const token = process.env.MURYA_VOICE_PREVIEW_TOKEN;
    if (!endpoint || !token) return error(503, "Pronunciation review unavailable");

    try {
      const destination = new URL(`/api/${route}`, endpoint);
      if (destination.protocol !== "https:") return error(503, "Pronunciation review unavailable");
      for (const key of ["status", "surface", "limit"]) {
        const value = url.searchParams.get(key);
        if (value !== null) destination.searchParams.set(key, value);
      }

      const headers = new Headers({ Authorization: `Bearer ${token}` });
      for (const key of ["content-type", "origin", "x-contributor-id"]) {
        const value = request.headers.get(key);
        if (value) headers.set(key, value);
      }
      const session = request.headers.get("cookie")?.split(/;\s*/).find((cookie) => cookie.startsWith("murya_admin_session="));
      if (route.startsWith("admin/") && session) headers.set("cookie", session);

      const body = request.method === "POST" ? await request.arrayBuffer() : undefined;
      if (body && body.byteLength > 4 * 1024 * 1024) return error(413, "Recording is too large");

      const upstream = await fetch(destination, {
        method: request.method, headers, body, redirect: "error", signal: AbortSignal.timeout(25000),
      });
      const responseHeaders = new Headers({ "Cache-Control": "no-store" });
      for (const key of ["content-type", "content-disposition", "retry-after", "set-cookie"]) {
        const value = upstream.headers.get(key);
        if (value) responseHeaders.set(key, value);
      }
      return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
    } catch {
      return error(502, "Pronunciation review unavailable");
    }
  },
};
