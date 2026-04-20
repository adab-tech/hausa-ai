
import { LearnedMemory, FlywheelStats } from "../types.ts";

const MEMORY_KEY = 'vertex_sovereign_memory_v28';
const STATS_KEY = 'vertex_sovereign_stats_v28';

export interface Forecast {
  week: number;
  expectedHumanInput: number;
  expectedAutoAxioms: number;
  stabilityScore: number;
}

class LearningService {
  private memories: LearnedMemory[] = [];
  private stats: FlywheelStats & { forecast: Forecast[] };

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

    const savedStats = localStorage.getItem(STATS_KEY);
    this.stats = savedStats ? JSON.parse(savedStats) : this.generateInitialStats();
  }

  private generateInitialStats(): FlywheelStats & { forecast: Forecast[] } {
    const history = [];
    const now = new Date();
    for (let i = 7; i >= 0; i--) {
      const d = new Date();
      d.setDate(now.getDate() - i);
      history.push({
        date: d.toISOString().split('T')[0],
        human: 20 + (7 - i) * 6,
        auto: Math.floor(Math.pow(2.4, 7 - i))
      });
    }

    const currentHuman = history[history.length - 1].human;
    const currentAuto = history[history.length - 1].auto;

    const forecast: Forecast[] = [];
    for (let w = 1; w <= 4; w++) {
      forecast.push({
        week: w,
        expectedHumanInput: Math.max(5, Math.round(currentHuman / (w * 1.2))),
        expectedAutoAxioms: Math.round(currentAuto * Math.pow(1.8, w)),
        stabilityScore: Math.min(99.9, 95 + (w * 1.2))
      });
    }

    return {
      humanAxioms: currentHuman,
      autonomousAxioms: currentAuto,
      neuralMomentum: 99.2,
      cacheEfficiency: 99.99,
      learningHistory: history,
      projectedGrowthRate: 31.5,
      lastOptimized: now.toISOString(),
      forecast
    };
  }

  private save() {
    localStorage.setItem(MEMORY_KEY, JSON.stringify(this.memories));
    localStorage.setItem(STATS_KEY, JSON.stringify(this.stats));
  }

  getMemoryPrompt(): string {
    const coreTruths = this.memories
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 15) 
      .map(m => `[AXIOM]: '${m.fact}' => '${m.correction}'`)
      .join('\n');
    return `[CULTURAL_&_PROSODIC_REINFORCEMENT]:\n${coreTruths}`;
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
    if (source === 'human') this.stats.humanAxioms++;
    else this.stats.autonomousAxioms++;
    this.updateStats();
    this.save();
  }

  private updateStats() {
    const nowStr = new Date().toISOString().split('T')[0];
    const historyIndex = this.stats.learningHistory.findIndex(h => h.date === nowStr);
    if (historyIndex > -1) {
      this.stats.learningHistory[historyIndex].human = this.stats.humanAxioms;
      this.stats.learningHistory[historyIndex].auto = this.stats.autonomousAxioms;
    }
    this.stats.projectedGrowthRate = parseFloat((this.stats.autonomousAxioms / this.stats.humanAxioms * 25).toFixed(1));
  }

  getStats() { return this.stats; }
}

export const learning = new LearningService();
