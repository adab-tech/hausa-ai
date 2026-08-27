/** feedbackService.ts — public-facing contribution actions: thumbs up/down
 * on a reply, flagging a mispronunciation, and submitting community Q&A. */

import { BACKEND_URL, withContributor } from "./apiConfig.ts";

export async function recordFeedback(messageId: string, type: "up" | "down", text: string, correction?: string): Promise<void> {
  try {
    await fetch(`${BACKEND_URL}/api/feedback`, {
      method: "POST",
      headers: withContributor({ "Content-Type": "application/json" }),
      body: JSON.stringify({ messageId, type, text, correction: correction ?? "" }),
    });
  } catch (err) {
    console.error("Failed to record feedback:", err);
  }
}

export async function getFeedbackStats(): Promise<{ up: number; down: number; total: number } | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/feedback/stats`);
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch feedback stats:", err);
    return null;
  }
}

/** PUBLIC: a user reports a mispronunciation for a reviewer to fix. */
export async function flagPronunciation(text: string, speakerId: number | null = null, note?: string): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/pronunciation/flag`, {
      method: "POST",
      headers: withContributor({ "Content-Type": "application/json" }),
      credentials: "include",
      body: JSON.stringify({ text, speaker_id: speakerId, note }),
    });
    return res.ok;
  } catch (err) {
    console.error("Failed to flag pronunciation:", err);
    return false;
  }
}

/** PUBLIC: contribute a Hausa question + answer. Lands pending for owner approval. */
export async function submitQA(question: string, answer: string, topic?: string): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/qa/submit`, {
      method: "POST",
      headers: withContributor({ "Content-Type": "application/json" }),
      credentials: "include",
      body: JSON.stringify({ question, answer, topic }),
    });
    return res.ok;
  } catch (err) { console.error("Failed to submit Q&A:", err); return false; }
}

/** PUBLIC: a user records the correct pronunciation of a word/phrase (+ optional
 * note). Lands pending for the owner to approve — never served without approval. */
export async function submitUserPronunciation(text: string, speakerId: number | null, audio: Blob, note?: string): Promise<boolean> {
  try {
    const fd = new FormData();
    fd.append("text", text);
    if (speakerId !== null && speakerId !== undefined) fd.append("speaker_id", String(speakerId));
    if (note) fd.append("note", note);
    fd.append("audio", audio, "correction.webm");
    const res = await fetch(`${BACKEND_URL}/api/pronunciation/submit`, {
      method: "POST", headers: withContributor({}), credentials: "include", body: fd,
    });
    return res.ok;
  } catch (err) {
    console.error("Failed to submit user pronunciation:", err);
    return false;
  }
}
