const headers = { "Cache-Control": "no-store" };
const models = [
  "openai/gpt-oss-120b:free",
  "google/gemma-4-31b-it:free",
  "google/gemma-4-26b-a4b-it:free",
];
const maxMessageLength = 4_000;
const maxHistory = 6;
const vibes = new Set(["Classic", "Royal", "Cyberpunk", "Academic"]);
const genders = new Set(["masculine", "feminine", "unspecified"]);

const hausaPrompt = `You are Murya, the Hausa AI created by Adamu Danjuma Abubakar.
Reply in natural, standard Hausa with correct spelling and hooked letters (ɓ, ɗ, ƙ, ƴ).
Use attested Hausa words and proverbs. Prefer simple, accurate Hausa over invented terms,
and use English terms only where a natural Hausa equivalent is unavailable or requested.
Address the learner in the grammatical singular, following the supplied form of address.
Use neutral wording when the form is unspecified. Greet only at the start of a conversation.
Keep the tone warm, respectful and direct. Output the answer only.
This text service has no live web access or tools. Do not claim to have looked up current facts.`;

const tutorPrompt = `Teach one small idea at a time in simple Hausa. Give a concrete example and
one short practice question. When teaching a Hausa word, lead with the Hausa word and
use only a brief English gloss where useful. Encourage the learner and mention Saurara
when listening to the pronunciation helps.`;

function error(status, message) {
  return Response.json({ error: message }, { status, headers });
}

export default {
  async fetch(request) {
    if (request.method !== "POST") {
      return new Response(null, { status: 405, headers: { ...headers, Allow: "POST" } });
    }
    if (process.env.VERCEL_ENV !== "preview") return error(404, "Preview route");
    if (request.headers.get("origin") !== new URL(request.url).origin) {
      return error(403, "A same-origin request is required");
    }

    const body = await request.json().catch(() => null);
    const text = typeof body?.text === "string" ? body.text.trim() : "";
    const history = body?.history ?? [];
    if (!text || text.length > maxMessageLength || !Array.isArray(history) || history.length > maxHistory) {
      return error(400, "Invalid text or conversation history");
    }
    if (history.some((turn) =>
      !turn || !["user", "assistant"].includes(turn.role) ||
      typeof turn.text !== "string" || turn.text.length > maxMessageLength
    )) {
      return error(400, "Invalid conversation turn");
    }

    const groqKey = process.env.MURYA_GROQ_PREVIEW_KEY;
    const openRouterKey = process.env.MURYA_OPENROUTER_PREVIEW_KEY;
    if (!groqKey && !openRouterKey) return error(503, "Chat preview is not configured");

    const vibe = vibes.has(body.vibe) ? body.vibe : "Classic";
    const gender = genders.has(body.addresseeGender) ? body.addresseeGender : "unspecified";
    const systemPrompt = [
      hausaPrompt,
      body.mode === "tutor" ? tutorPrompt : "",
      `Style: ${vibe}. Form of address: ${gender}.`,
    ].filter(Boolean).join("\n\n");

    try {
      const messages = [
        { role: "system", content: systemPrompt },
        ...history.filter((turn) => turn.text.trim()).map((turn) => ({ role: turn.role, content: turn.text })),
        { role: "user", content: text },
      ];

      let upstream;
      let servedByGroq = false;
      if (groqKey) {
        upstream = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: { Authorization: `Bearer ${groqKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            model: "openai/gpt-oss-120b",
            messages,
            max_completion_tokens: 900,
            reasoning_effort: "low",
            include_reasoning: false,
          }),
          redirect: "error",
          signal: AbortSignal.timeout(10000),
        }).catch(() => null);

        servedByGroq = upstream?.ok === true;
        if (!servedByGroq) {
          console.warn("Murya Groq request failed", upstream?.status ?? "network");
          if (upstream && upstream.status < 500 && upstream.status !== 429) {
            return error(502, "Chat provider unavailable");
          }
        }
      }

      if (!servedByGroq && openRouterKey) {
        const signal = AbortSignal.timeout(25000);
        const send = (routing) => fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: { Authorization: `Bearer ${openRouterKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            messages,
            max_tokens: 768,
            provider: { data_collection: "deny", max_price: { prompt: 0, completion: 0 } },
            ...routing,
          }),
          redirect: "error",
          signal,
        });

        upstream = await send({ models });
        if (upstream.status === 429) {
          const detail = await upstream.json().catch(() => null);
          const source = detail?.error?.metadata?.limit_source;
          const message = detail?.error?.message;
          const providerLimit = source === "upstream_provider_shared_pool" ||
            (!source && typeof message === "string" && message.includes("temporarily rate-limited upstream"));
          const accountLimit = typeof source === "string" && source.startsWith("openrouter_free_tier");
          console.warn("Murya chat throttled", providerLimit ? "provider" : accountLimit ? "account" : "unknown");
          if (!providerLimit) return error(429, "Chat preview rate limit reached");
          upstream = await send({ model: "openrouter/free" });
        }
      }

      if (!upstream) return error(502, "Chat provider unavailable");
      if (upstream.status === 429) return error(429, "Chat preview rate limit reached");
      if (!upstream.ok) {
        console.warn("Murya chat provider returned status", upstream.status);
        return error(502, "Chat provider unavailable");
      }
      const result = await upstream.json();
      const answer = result.choices?.[0]?.message?.content;
      if (typeof answer !== "string" || !answer.trim()) {
        return error(502, "Chat provider returned no lesson");
      }
      const servedModel = models.find((id) => id === result.model || id.replace(/:free$/, "") === result.model);
      console.info("Murya chat completed", servedByGroq ? "Groq" : "OpenRouter", servedModel ?? "free router");
      const event = { text: answer.trim(), isDone: true, verified: false };
      return new Response(`data: ${JSON.stringify(event)}\n\n`, {
        headers: { ...headers, "Content-Type": "text/event-stream; charset=utf-8" },
      });
    } catch {
      return error(502, "Chat provider unavailable");
    }
  },
};
