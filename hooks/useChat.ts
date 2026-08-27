import { useEffect, useMemo, useState } from 'react';
import { Message, Role, Attachment, SovereignVibe, AddresseeGender } from '../types.ts';
import { gemini } from '../services/localService.ts';
import { learning } from '../services/learningService.ts';
import { AXIOM_PHRASES } from '../components/MessageItem.tsx';

/** The text chat thread: sending a message (streaming the reply), thumbs
 * up/down feedback, and the "thinking" placeholder's rotating axiom phrase. */
export function useChat(
  vibe: SovereignVibe,
  addresseeGender: AddresseeGender,
  learningMode: boolean
) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAxiomIndex, setCurrentAxiomIndex] = useState(0);
  const [feedbacks, setFeedbacks] = useState<Record<string, 'up' | 'down'>>({});

  useEffect(() => {
    let interval: number;
    if (isLoading) {
      interval = window.setInterval(() => {
        setCurrentAxiomIndex(prev => (prev + 1) % AXIOM_PHRASES.length);
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  // Record one privacy-preserving visit per app load (no IP; geography by
  // browser timezone, uniqueness by the anonymous contributor id). Fire once.
  useEffect(() => { gemini.recordVisit(); }, []);

  const handleSendMessage = async (
    inputText: string,
    attachments: Attachment[],
    onSent: () => void
  ) => {
    if (!inputText.trim() && attachments.length === 0) return;

    const currentInput = inputText;
    const currentAttachments = [...attachments];

    const userMsg: Message = {
      id: Date.now().toString(),
      role: Role.user,
      text: currentInput,
      attachments: currentAttachments,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    onSent(); // clears inputText/attachments in the caller

    const aiMsgId = (Date.now() + 1).toString();
    const aiMsgPlaceholder: Message = {
      id: aiMsgId,
      role: Role.assistant,
      text: "",
      isThinking: true,
      timestamp: new Date(),
      modelTier: 'Pro'
    };
    setMessages(prev => [...prev, aiMsgPlaceholder]);
    setIsLoading(true);

    try {
      const stream = gemini.unifiedExchange(currentInput, messages, currentAttachments, vibe, addresseeGender, learningMode ? 'tutor' : 'assistant');
      for await (const chunk of stream) {
        setMessages(prev => prev.map(m => m.id === aiMsgId ? {
          ...m,
          text: chunk.text,
          attachments: chunk.attachments,
          groundingSources: chunk.groundingSources,
          isThinking: !chunk.isDone,
          modelTier: chunk.tier as any,
          verified: chunk.verified,
          normalized: chunk.normalized,
          toneMapped: chunk.toneMapped
        } : m));
      }
    } catch (err) {
      setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: "Gafara dai, an samu kuskure. A sake gwadawa.", isThinking: false } : m));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = (messageId: string, feedback: 'up' | 'down', correction?: string) => {
    if (feedbacks[messageId]) return;
    setFeedbacks(prev => ({ ...prev, [messageId]: feedback }));
    const msg = messages.find(m => m.id === messageId);
    if (msg) {
      learning.recordFeedback(messageId, feedback, msg.text);
      gemini.recordFeedback(messageId, feedback, msg.text, correction);
    }
  };

  // Live-voice turns stay in `messages` for conversational memory (see the
  // fromLiveVoice comment on the Message type) but never render as chat
  // bubbles -- a live call should read as a real phone call, not a
  // transcription window.
  const visibleMessages = useMemo(
    () => messages.filter(m => !m.fromLiveVoice),
    [messages]
  );

  return {
    messages,
    setMessages,
    visibleMessages,
    isLoading,
    currentAxiomIndex,
    feedbacks,
    handleSendMessage,
    handleFeedback,
  };
}
