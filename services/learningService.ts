
import { LearnedMemory } from "../types.ts";

const MEMORY_KEY = 'vertex_sovereign_memory_v28';

class LearningService {
  private memories: LearnedMemory[] = [];

  constructor() {
    const savedMemories = localStorage.getItem(MEMORY_KEY);
    this.memories = savedMemories ? JSON.parse(savedMemories) : [];

    if (this.memories.length === 0) {
      this.memories = [
        { fact: "Litvinova 2024: Tonal Mapping", category: "phonetic", correction: "Melodies map R-to-L onto prosodic words. The mora is the TBU.", timestamp: new Date().toISOString(), weight: 1200, source: 'human' },
        { fact: "Toneme Deletion", category: "phonetic", correction: "Light initial syllables delete the first toneme of the melody.", timestamp: new Date().toISOString(), weight: 1150, source: 'human' },
        { fact: "Kunya (Modesty)", category: "autonomous", correction: "Hausa cultural interaction requires indirect speech for sensitive topics.", timestamp: new Date().toISOString(), weight: 1200, source: 'human' },
        { fact: "Girmamawa (Respect)", category: "autonomous", correction: "Always address elders and superiors with 'Ku' (plural) and honorifics like 'Ranka ya dade'.", timestamp: new Date().toISOString(), weight: 1180, source: 'human' },
        { fact: "Karin Magana (Proverbs)", category: "autonomous", correction: "Proverbs are the 'soul' of Hausa discourse; they must be contextually relevant and dignified.", timestamp: new Date().toISOString(), weight: 1100, source: 'human' },
        { fact: "Heavy Syllable Constraint", category: "phonetic", correction: "Contours (H-L) allowed ONLY on heavy CVː or CVC syllables.", timestamp: new Date().toISOString(), weight: 1050, source: 'human' },
        { fact: "Newman 1996 Protocol", category: "phonetic", correction: "Strict hooked letters (ɓ, ɗ, ƙ) and glottal 'y.", timestamp: new Date().toISOString(), weight: 1000, source: 'human' }
      ];
    }
  }

  private save() {
    localStorage.setItem(MEMORY_KEY, JSON.stringify(this.memories));
  }

  getMemoryPrompt(): string {
    const coreTruths = this.memories
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 15)
      .map(m => `[AXIOM]: '${m.fact}' => '${m.correction}'`)
      .join('\n');

    const WAXAL_FEW_SHOTS = [
      {
        user: "Wannan saniya ce mai launin fari da baki.",
        assistant: "Ranka ya daɗe, lallai wannan sáníyà cé máí làùnín fàrí dá bákí mai ban sha'awa."
      },
      {
        user: "Bishiyar ayaba koriya shar da nunannu 'ya'yanta guda uku.",
        assistant: "Barka da yini. Ga bìshìyár áyábà kòrìyá shár dá núnánnù ƴáƴántà gúdà úkú a gona."
      },
      {
        user: "Sittin a raba wa mutum biyu= ya zama talatin.",
        assistant: "Godiya nake. Idan aka raba sìttín ga mútané bíyù, kówá zai samu tàlàtín."
      }
    ];

    const fewShots = WAXAL_FEW_SHOTS
      .map(fs => `[INPUT]: ${fs.user}\n[SOVEREIGN_RESPONSE]: ${fs.assistant}`)
      .join('\n\n');

    return `[CULTURAL_&_PROSODIC_REINFORCEMENT]:\n${coreTruths}\n\n[FEW_SHOT_EXAMPLES]:\n${fewShots}`;
  }

  /**
   * Adjusts axiom weights based on user feedback so future prompts favor
   * axioms the user actually confirmed as relevant. This directly changes
   * getMemoryPrompt() output — it is not a cosmetic counter.
   */
  recordFeedback(messageId: string, type: 'up' | 'down', messageText?: string) {
    const delta = type === 'up' ? 100 : -150;

    this.memories = this.memories.map(m => {
      let isRelevant = false;
      if (messageText) {
        const txt = messageText.toLowerCase();
        if (m.category === 'phonetic') {
          if (m.fact.includes("Tonal") && /[àáèéìíòóùú]/.test(messageText)) isRelevant = true;
          if (m.fact.includes("hooked") && /[ɓɗƙƴ]/.test(messageText)) isRelevant = true;
        } else if (m.category === 'autonomous') {
          if (m.fact.includes("Proverbs") && /karin magana/i.test(txt)) isRelevant = true;
          if (m.fact.includes("Respect") && /\b(ku|kun|muku|sun)\b/i.test(txt)) isRelevant = true;
          if (m.fact.includes("Kunya") && /kunya/i.test(txt)) isRelevant = true;
        }
      }
      if (isRelevant) {
        return { ...m, weight: Math.max(0, m.weight + delta) };
      }
      return m;
    });

    this.save();
  }

  addMemory(memory: Partial<LearnedMemory>) {
    const source = memory.source || 'human';
    this.memories.push({
      fact: memory.fact || 'Tonal Alignment',
      category: memory.category || 'phonetic',
      correction: memory.correction || '',
      timestamp: new Date().toISOString(),
      weight: source === 'human' ? 950 : 300,
      source: source
    });
    this.save();
  }
}

export const learning = new LearningService();
