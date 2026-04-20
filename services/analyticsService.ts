
import { VoiceSettings } from "../types";

export interface AnalyticsData {
  voiceUsage: Record<string, number>;
  speedPreferences: number[];
  totalVoiceSessions: number;
  totalTextMessages: number;
  lastUpdated: string;
}

const STORAGE_KEY = 'gwarzo_analytics_v1';

class AnalyticsService {
  private data: AnalyticsData;

  constructor() {
    const saved = localStorage.getItem(STORAGE_KEY);
    this.data = saved ? JSON.parse(saved) : {
      voiceUsage: {},
      speedPreferences: [],
      totalVoiceSessions: 0,
      totalTextMessages: 0,
      lastUpdated: new Date().toISOString()
    };
  }

  private save() {
    this.data.lastUpdated = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
  }

  logVoiceSession(settings: VoiceSettings) {
    this.data.totalVoiceSessions++;
    this.data.voiceUsage[settings.voiceName] = (this.data.voiceUsage[settings.voiceName] || 0) + 1;
    this.data.speedPreferences.push(settings.speed);
    // Keep only last 100 for moving average
    if (this.data.speedPreferences.length > 100) this.data.speedPreferences.shift();
    this.save();
  }

  logTextMessage() {
    this.data.totalTextMessages++;
    this.save();
  }

  getInsights() {
    const totalVoices = Object.values(this.data.voiceUsage).reduce((a, b) => a + b, 0);
    const avgSpeed = this.data.speedPreferences.length > 0 
      ? this.data.speedPreferences.reduce((a, b) => a + b, 0) / this.data.speedPreferences.length 
      : 1.0;

    return {
      ...this.data,
      voicePopularity: Object.entries(this.data.voiceUsage).map(([name, count]) => ({
        name,
        percentage: totalVoices > 0 ? Math.round((count / totalVoices) * 100) : 0
      })).sort((a, b) => b.percentage - a.percentage),
      avgSpeed: avgSpeed.toFixed(2)
    };
  }

  reset() {
    localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  }
}

export const analytics = new AnalyticsService();
