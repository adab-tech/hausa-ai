
export enum Role {
  user = 'user',
  assistant = 'assistant'
}

export type HausaDialect = 'Kano (Dabo)' | 'Sokoto (Sakkwatawa)' | 'Zaria (Zazzagawa)' | 'Borno (Kanuri-Hausa)' | 'International';
export type SovereignVibe = 'Classic' | 'Royal' | 'Cyberpunk' | 'Academic';

export interface Attachment {
  type: 'image' | 'audio' | 'video';
  data?: string; 
  uri?: string; 
  name: string;
  mimeType: string;
}

export interface VoiceSettings {
  voiceName: 'Kore' | 'Zephyr' | 'Puck' | 'Charon' | 'Fenrir';
  speed: number;
  dialect: HausaDialect;
  timbre: 'Deep' | 'Bright' | 'Authoritative' | 'Gentle';
}

export interface Message {
  id: string;
  role: Role;
  text: string;
  attachments?: Attachment[];
  groundingSources?: Array<{ title: string; uri: string; type?: string }>;
  isThinking?: boolean;
  verified?: boolean;
  timestamp: Date;
  modelTier?: 'Flash' | 'Pro';
}

export type AspectRatio = '1:1' | '2:3' | '3:2' | '3:4' | '4:3' | '9:16' | '16:9' | '21:9';
export type ImageSize = '1K' | '2K' | '4K';

export interface GenSettings {
  aspectRatio: AspectRatio;
  imageSize: ImageSize;
  thinkingMode: boolean;
  fastMode: boolean;
  vibe: SovereignVibe;
}

export interface LearnedMemory {
  fact: string;
  category: 'current' | 'dialect' | 'general' | 'phonetic' | 'autonomous';
  correction: string;
  timestamp: string;
  weight: number;
  source: 'human' | 'autonomous';
}

export interface FlywheelStats {
  humanAxioms: number;
  autonomousAxioms: number;
  neuralMomentum: number;
  cacheEfficiency: number;
  learningHistory: Array<{ date: string; human: number; auto: number }>;
  projectedGrowthRate: number; // Percentage
  lastOptimized: string;
}
