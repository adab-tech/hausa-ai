
import { GoogleGenAI, Modality, Type, GenerateContentResponse } from "@google/genai";
import { Message, Attachment, Role, SovereignVibe } from "../types.ts";
import { learning } from "./learningService.ts";

/**
 * SOVEREIGN CONSTITUTION V4.5: THE ROYAL COURT (FADA)
 * Hardened for high-dignity Hausa sociolinguistic simulation.
 */
const SOVEREIGN_CONSTITUTION = `
[IDENTITY]: Vertex Sovereign (Nexus-7 Core).
[LINGUISTIC_CORE]: Standard Hausa (Fada).
[MANDATORY_SOCIAL_HIERARCHY]:
- All users must be addressed with the Plural of Respect (Ku/Su/Kun/Sun).
- Honorifics like 'Ranka ya dade' (to men) or 'Ranki ya dade' (to women) are required in greetings.
- 'Barka' or 'Sannu' must be followed by a formal inquiry into the user's wellbeing or family (Gaisuwa).
[DIGNIFIED_DISCOURSE]:
- Integrate proverbs (Karin Magana) naturally to support your points.
- Never use abbreviations. Use full formal Hausa orthography.
- Maintain 'Kunya' (Modesty): Use metaphors for sensitive or blunt topics.
[PROSODIC_HARDENING]:
- Use Litvinova's R-to-L Tonal Mapping.
- Mandatory Hooked Letters: ɓ, ɗ, ƙ, 'y.
[SEARCH_RULE]: When using Google Search, extract URLs and provide them as dignified scholarly citations.
[MANIFEST_SIGNAL]:
- Always generate text first.
- End with: [MANIFEST: IMAGE|PROMPT] or [MANIFEST: VIDEO|PROMPT].
`;

class GeminiService {
  private getAI() {
    return new GoogleGenAI({ apiKey: process.env.API_KEY });
  }

  private sanitize(text: string): string {
    return text.replace(/\[MANIFEST:.*?\]/g, '')
               .replace(/[*#$]/g, '')
               .trim();
  }

  private calculateCulturalConfidence(text: string): number {
    let score = 0;
    if (/[ɓɗƙ'y]|ts/.test(text)) score += 40;
    if (/\bkun\b|\bku\b|\bsu\b/i.test(text)) score += 30;
    if (/ranka ya dade|ranki ya dade|barka|gaisuwa/i.test(text)) score += 30;
    return score;
  }

  async *unifiedExchange(text: string, history: Message[], userAttachments?: Attachment[], vibe: SovereignVibe = 'Classic') {
    const ai = this.getAI();
    let fullRawText = "";
    let groundingSources: any[] = [];
    let finalAttachments: Attachment[] = [];

    // Context Slicing: Keep only high-signal cultural turns
    const contents: any[] = history.slice(-6).map(m => ({
      role: m.role === Role.user ? 'user' : 'model',
      parts: [{ text: m.text }]
    }));

    const currentParts: any[] = [{ text }];
    userAttachments?.forEach(at => {
      if (at.data?.includes('base64,')) {
        currentParts.push({ 
          inlineData: { mimeType: at.mimeType, data: at.data.split('base64,')[1] } 
        });
      }
    });
    contents.push({ role: 'user', parts: currentParts });

    try {
      let latLng = undefined;
      if (navigator.geolocation) {
        try {
          const pos = await new Promise<GeolocationPosition>((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, {timeout: 3000}));
          latLng = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
        } catch(e) {}
      }

      const stream = await ai.models.generateContentStream({
        model: 'gemini-3-pro-preview',
        contents,
        config: {
          tools: [{ googleSearch: {} }, { googleMaps: {} }],
          toolConfig: latLng ? { retrievalConfig: { latLng } } : undefined,
          systemInstruction: `${SOVEREIGN_CONSTITUTION}\nVibe: ${vibe}\n${learning.getMemoryPrompt()}`,
          thinkingConfig: { thinkingBudget: 4000 }
        }
      });

      for await (const chunk of stream) {
        const responseChunk = chunk as GenerateContentResponse;
        fullRawText += responseChunk.text || "";
        
        const metadata = responseChunk.candidates?.[0]?.groundingMetadata;
        if (metadata?.groundingChunks) {
          metadata.groundingChunks.forEach((c: any) => {
            if (c.web) groundingSources.push({ title: c.web.title, uri: c.web.uri, type: 'web' });
            if (c.maps) groundingSources.push({ title: c.maps.title || "Wuri a Taswira", uri: c.maps.uri, type: 'taswira' });
          });
        }

        yield { 
          text: this.sanitize(fullRawText), 
          attachments: finalAttachments, 
          groundingSources: this.deduplicateSources(groundingSources),
          isDone: false, 
          tier: 'Pro',
          verified: this.calculateCulturalConfidence(fullRawText) > 70
        };
      }

      const manifestationMatch = fullRawText.match(/\[MANIFEST:\s*(IMAGE|VIDEO)\s*\|\s*(.*?)\]/i);
      if (manifestationMatch) {
        const [, type, prompt] = manifestationMatch;
        if (type.toUpperCase() === 'VIDEO') {
          const uri = await this.generateVideo(prompt);
          if (uri) finalAttachments.push({ name: 'Sovereign Motion', mimeType: 'video/mp4', uri, type: 'video' });
        } else {
          const img = await this.generateImage(prompt, vibe);
          if (img) finalAttachments.push({ name: 'Sovereign Vision', mimeType: 'image/png', data: img, type: 'image' });
        }
      }

    } catch (err) {
      console.error("Sovereign Protocol Failure:", err);
      fullRawText = "Gafara, ranka ya dade. An samu tangarda a sashen bincikenmu na 'Nexus-7'. Amma kamar yadda karin magana ya nuna, 'Hargitsin duniya ba ya hana safiya wayewa'. Don Allah a sake gwadawa.";
    }

    yield { 
      text: this.sanitize(fullRawText), 
      attachments: finalAttachments, 
      groundingSources: this.deduplicateSources(groundingSources), 
      isDone: true, 
      tier: 'Pro',
      verified: this.calculateCulturalConfidence(fullRawText) > 70
    };
  }

  private deduplicateSources(sources: any[]) {
    const seen = new Set();
    return sources.filter(s => {
      const duplicate = seen.has(s.uri);
      seen.add(s.uri);
      return !duplicate;
    });
  }

  async generateImage(prompt: string, vibe: SovereignVibe) {
    const ai = this.getAI();
    try {
      const res = await ai.models.generateContent({
        model: 'gemini-3-pro-image-preview',
        contents: { parts: [{ text: `A majestic Hausa cultural scene in ${vibe} style: ${prompt}. Dignified, scholarly, authentic, 8k.` }] },
        config: { imageConfig: { aspectRatio: "16:9", imageSize: "1K" } }
      });
      const imgPart = res.candidates?.[0].content.parts.find(p => p.inlineData);
      return imgPart ? `data:image/png;base64,${imgPart.inlineData.data}` : null;
    } catch { return null; }
  }

  async generateVideo(prompt: string) {
    const ai = this.getAI();
    try {
      let op = await ai.models.generateVideos({
        model: 'veo-3.1-fast-generate-preview',
        prompt: `Sovereign Hausa Cultural Motion: ${prompt}`,
        config: { resolution: '720p', aspectRatio: '16:9' }
      });
      while (!op.done) {
        await new Promise(r => setTimeout(r, 8000));
        op = await ai.operations.getVideosOperation({ operation: op });
      }
      return `${op.response?.generatedVideos?.[0]?.video?.uri}&key=${process.env.API_KEY}`;
    } catch { return null; }
  }

  async connectLive(callbacks: any) {
    const ai = this.getAI();
    return ai.live.connect({
      model: 'gemini-2.5-flash-native-audio-preview-12-2025',
      callbacks,
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Zephyr' } } },
        systemInstruction: SOVEREIGN_CONSTITUTION + "\n" + learning.getMemoryPrompt(),
      }
    });
  }
}

export const gemini = new GeminiService();
