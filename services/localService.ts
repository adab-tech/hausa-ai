/**
 * localService.ts — the `gemini` facade every component imports.
 *
 * The actual implementations live in domain services (chatService,
 * dictionaryService, feedbackService, visitorAnalyticsService,
 * waxalService, adminService) — this file just assembles them into the
 * single object every call site already uses, so nothing outside
 * services/ had to change when the old 800-line god-file was split up.
 */

import * as chat from "./chatService.ts";
import * as dictionary from "./dictionaryService.ts";
import * as feedback from "./feedbackService.ts";
import * as visitorAnalytics from "./visitorAnalyticsService.ts";
import * as waxal from "./waxalService.ts";
import * as admin from "./adminService.ts";

export { BACKEND_URL, getContributorId } from "./apiConfig.ts";

export const gemini = {
  // chatService
  unifiedExchange: chat.unifiedExchange,
  generateImage: chat.generateImage,
  generateVideo: chat.generateVideo,
  connectLive: chat.connectLive,
  getTtsUrl: chat.getTtsUrl,
  streamDocument: chat.streamDocument,

  // dictionaryService
  searchDictionary: dictionary.searchDictionary,

  // feedbackService
  recordFeedback: feedback.recordFeedback,
  getFeedbackStats: feedback.getFeedbackStats,
  flagPronunciation: feedback.flagPronunciation,
  submitQA: feedback.submitQA,
  submitUserPronunciation: feedback.submitUserPronunciation,

  // visitorAnalyticsService
  recordVisit: visitorAnalytics.recordVisit,
  getAnalytics: visitorAnalytics.getAnalytics,

  // waxalService
  getWaxalStats: waxal.getWaxalStats,
  getWaxalSamples: waxal.getWaxalSamples,
  getWaxalAudioUrl: waxal.getWaxalAudioUrl,

  // adminService
  adminLogin: admin.adminLogin,
  changePassword: admin.changePassword,
  adminLogout: admin.adminLogout,
  adminMe: admin.adminMe,
  getAuditLog: admin.getAuditLog,
  getCorrections: admin.getCorrections,
  reviewCorrection: admin.reviewCorrection,
  getQA: admin.getQA,
  setQAStatus: admin.setQAStatus,
  deleteQA: admin.deleteQA,
  exportQA: admin.exportQA,
  getPronunciations: admin.getPronunciations,
  submitPronunciation: admin.submitPronunciation,
  recordPronunciation: admin.recordPronunciation,
  setPronunciationStatus: admin.setPronunciationStatus,
  deletePronunciation: admin.deletePronunciation,
  exportPronunciationCorpus: admin.exportPronunciationCorpus,
  pronunciationAudioUrl: admin.pronunciationAudioUrl,
};
