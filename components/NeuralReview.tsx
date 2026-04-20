
import React, { useState } from 'react';
import { learning } from '../services/learningService.ts';
import { ArewaLogo } from './ArewaLogo.tsx';

export const NeuralReview: React.FC<{ onClose: () => void; onOpenWhitePaper?: () => void }> = ({ onClose, onOpenWhitePaper }) => {
  const stats = learning.getStats() as any;
  const [activeTab, setActiveTab] = useState<'telemetry' | 'matrix' | 'phonology' | 'vision'>('telemetry');
  
  const competitiveEdge = [
    { metric: 'Scholarly Sources', sovereign: '7 (Nexus-7 Core)', others: 'Generic Web Data', advantage: 'Primary Grounding' },
    { metric: 'Prosodic Logic', sovereign: 'Litvinova R-to-L', others: 'Statistical Stress', advantage: 'Native Rhythm' },
    { metric: 'Unit of Tone', sovereign: 'Mora-Aware', others: 'Syllable-Approx', advantage: 'Phonetic Truth' },
    { metric: 'Purity', sovereign: 'Hausar Fada', others: 'Mixed (Enghausa)', advantage: 'Zero-Switch' },
    { metric: 'Phonetics', sovereign: 'Newman Inventory', others: 'Simplified Latin', advantage: 'Deep Fidelity' }
  ];

  const primaryAxioms = [
    { rule: "Litvinova (2024)", desc: "Right-to-Left Tonal Melody Mapping onto Prosodic Words.", proof: "Natural cadence in complex plurals." },
    { rule: "Toneme Deletion", desc: "Light initial syllables (CV) drop the first melody toneme.", proof: "Elimination of 'AI accent' in Hausa." },
    { rule: "Mora TBU", desc: "Contours (H-L sequences) restricted to heavy syllables.", proof: "Rhythmic etymological accuracy." },
    { rule: "Newman (1996)", desc: "Primary Inventory of ɓ, ɗ, ƙ, ts, c'.", proof: "Structural integrity of Standard Hausa." }
  ];

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-8 animate-reveal">
      <div className="absolute inset-0 bg-black/98 backdrop-blur-3xl" onClick={onClose}></div>
      
      <div className="relative w-full max-w-6xl bg-obsidian border border-silk-gold/20 rounded-[30px] sm:rounded-[80px] shadow-[0_0_100px_rgba(212,175,55,0.15)] overflow-hidden flex flex-col max-h-[95vh]">
        <header className="p-6 sm:p-12 md:p-16 pb-4 sm:pb-8 flex flex-col md:flex-row items-center justify-between border-b border-silk-gold/10 gap-6">
          <div className="flex items-center gap-6 sm:gap-10 text-center md:text-left">
            <ArewaLogo size={60} className="sm:w-20 sm:h-20" active />
            <div>
              <h2 className="font-serif italic text-3xl sm:text-5xl md:text-6xl text-silk-gold leading-none">The Matrix</h2>
              <p className="text-[8px] sm:text-[10px] opacity-40 uppercase tracking-[0.4em] sm:tracking-[0.8em] mt-2 text-white">Linguistic Grounding: Prosodic Core</p>
            </div>
          </div>
          <div className="flex bg-white/5 p-1.5 rounded-full w-full md:w-auto overflow-x-auto no-scrollbar border border-white/5">
            {['telemetry', 'matrix', 'phonology', 'vision'].map((tab) => (
              <button 
                key={tab}
                onClick={() => setActiveTab(tab as any)}
                className={`flex-1 md:flex-none px-6 sm:px-8 py-2 sm:py-3 rounded-full text-[8px] sm:text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === tab ? 'bg-silk-gold text-black' : 'text-white/40 hover:text-white'}`}
              >
                {tab}
              </button>
            ))}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6 sm:p-12 md:p-16 space-y-12 no-scrollbar">
          {activeTab === 'telemetry' && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-8 animate-reveal">
              {[
                { label: 'Scholarly Nexus', val: '7', sub: 'Primary Research' },
                { label: 'Neural Axioms', val: stats.humanAxioms + stats.autonomousAxioms, sub: 'Prosodic Gates' },
                { label: 'Tone Rule', val: 'R→L', sub: 'Litvinova Standard' },
                { label: 'Stability', val: stats.forecast[0].stabilityScore + '%', sub: 'Linguistic Consistency' }
              ].map((item, i) => (
                <div key={i} className="p-8 sm:p-12 rounded-[40px] sm:rounded-[60px] bg-white/[0.02] border border-white/5 text-center group hover:border-silk-gold/30 transition-all duration-700">
                  <span className="text-[8px] sm:text-[10px] text-white/30 uppercase tracking-widest block mb-4">{item.label}</span>
                  <div className="text-4xl sm:text-7xl md:text-8xl font-serif italic text-silk-gold group-hover:scale-110 transition-transform">{item.val}</div>
                  <p className="text-[7px] sm:text-[9px] text-white/20 mt-4 uppercase tracking-widest">{item.sub}</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'phonology' && (
            <div className="space-y-12 animate-reveal">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {primaryAxioms.map((ax, i) => (
                  <div key={i} className="p-10 rounded-[40px] border border-silk-gold/10 bg-silk-gold/[0.02] flex flex-col gap-4">
                    <span className="text-silk-gold font-mono text-[9px] uppercase tracking-widest">Prosodic Axiom {i + 1}: {ax.rule}</span>
                    <h3 className="text-3xl font-serif italic text-white/90">{ax.desc}</h3>
                    <div className="h-[1px] w-full bg-silk-gold/20 my-2"></div>
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-silk-gold shadow-[0_0_10px_#D4AF37]"></div>
                      <span className="text-[10px] text-white/40 uppercase tracking-widest">Implementation: {ax.proof}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-12 rounded-[60px] bg-white/5 border border-white/10 text-center">
                 <p className="text-xl sm:text-3xl font-serif italic text-white/60 leading-relaxed">
                   "By implementing Right-to-Left tone mapping, we treat Hausa not as a translated language, but as a primary prosodic system."
                 </p>
              </div>
            </div>
          )}

          {activeTab === 'matrix' && (
            <div className="animate-reveal overflow-x-auto">
               <div className="min-w-[700px] overflow-hidden rounded-[40px] sm:rounded-[60px] border border-white/10 bg-white/[0.01]">
                <table className="w-full text-left">
                  <thead className="bg-white/5 text-[10px] uppercase tracking-[0.3em] text-white/50">
                    <tr>
                      <th className="p-10">Neural Metric</th>
                      <th className="p-10 text-silk-gold">Vertex Sovereign (Prosodic)</th>
                      <th className="p-10">Standard AI Models</th>
                    </tr>
                  </thead>
                  <tbody className="text-xl sm:text-2xl">
                    {competitiveEdge.map((row, i) => (
                      <tr key={i} className="border-t border-white/5 hover:bg-white/[0.03] transition-colors">
                        <td className="p-10 font-serif italic text-white/80">{row.metric}</td>
                        <td className="p-10 text-silk-gold font-bold">{row.sovereign}</td>
                        <td className="p-10 text-white/10">{row.others}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'vision' && (
            <div className="max-w-4xl mx-auto space-y-16 py-12 text-white animate-reveal text-center">
              <div className="flex justify-center"><ArewaLogo size={100} className="sm:w-32 sm:h-32" active /></div>
              <h3 className="font-serif italic text-6xl sm:text-8xl md:text-9xl text-silk-gold leading-tight">Digital Prosody</h3>
              <p className="text-white/50 text-2xl sm:text-4xl font-light italic leading-relaxed px-4">
                We have moved beyond words. Vertex Sovereign calculates the vibration of Standard Hausa through the laws of moraic TBUs and R-to-L melody mapping.
              </p>
              <div className="p-12 rounded-[80px] bg-gradient-to-br from-silk-gold/10 to-transparent border border-silk-gold/20 flex flex-col md:flex-row items-center justify-between gap-8">
                <div className="text-center md:text-left">
                  <p className="text-silk-gold text-[10px] uppercase tracking-[0.5em] font-black mb-4">Lead Architect</p>
                  <p className="text-4xl sm:text-6xl font-serif italic">Adamu Danjuma Abubakar</p>
                </div>
                {onOpenWhitePaper && (
                   <button 
                     onClick={() => { onClose(); onOpenWhitePaper(); }}
                     className="px-10 py-5 rounded-full bg-silk-gold text-black text-[12px] font-black uppercase tracking-widest hover:scale-110 active:scale-95 transition-all shadow-2xl"
                   >
                     Read White Paper
                   </button>
                )}
              </div>
            </div>
          )}
        </div>
        
        <footer className="p-8 bg-white/[0.02] border-t border-white/5 flex justify-between items-center px-16 text-[9px] text-white/20 uppercase tracking-[0.5em] font-black italic">
           <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-silk-gold animate-pulse"></div>
              <span>Grounding Nexus: Litvinova Standard</span>
           </div>
           <span>System Prosody: 100% Scholarly Verified</span>
        </footer>
      </div>
    </div>
  );
};
