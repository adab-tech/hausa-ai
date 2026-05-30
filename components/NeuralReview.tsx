
import React, { useState, useEffect, useRef } from 'react';
import { learning } from '../services/learningService.ts';
import { ArewaLogo } from './ArewaLogo.tsx';
import { gemini } from '../services/localService.ts';

export const NeuralReview: React.FC<{ onClose: () => void; onOpenWhitePaper?: () => void }> = ({ onClose, onOpenWhitePaper }) => {
  const stats = learning.getStats() as any;
  const [activeTab, setActiveTab] = useState<'telemetry' | 'matrix' | 'phonology' | 'vision' | 'waxal'>('telemetry');

  // WAXAL explorer states
  const [waxalStats, setWaxalStats] = useState<any>(null);
  const [waxalSamples, setWaxalSamples] = useState<any[]>([]);
  const [waxalPage, setWaxalPage] = useState(1);
  const [waxalTotalPages, setWaxalTotalPages] = useState(1);
  const [waxalTotalCount, setWaxalTotalCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [speakerFilter, setSpeakerFilter] = useState('');
  const [genderFilter, setGenderFilter] = useState('');
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (activeTab === 'waxal') {
      gemini.getWaxalStats().then(data => {
        if (data) setWaxalStats(data);
      });
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'waxal') {
      gemini.getWaxalSamples(
        waxalPage,
        8,
        speakerFilter || undefined,
        genderFilter || undefined,
        searchQuery || undefined
      ).then(data => {
        if (data) {
          setWaxalSamples(data.samples || []);
          setWaxalTotalPages(data.total_pages || 1);
          setWaxalTotalCount(data.total_count || 0);
        }
      });
    }
  }, [activeTab, waxalPage, speakerFilter, genderFilter, searchQuery]);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  const playAudio = (filename: string) => {
    const url = gemini.getWaxalAudioUrl(filename);
    if (playingAudio === filename) {
      if (audioRef.current) {
        audioRef.current.pause();
        setPlayingAudio(null);
      }
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(url);
      audioRef.current = audio;
      setPlayingAudio(filename);
      audio.play();
      audio.onended = () => {
        setPlayingAudio(null);
      };
      audio.onerror = () => {
        console.error("Audio playback error");
        setPlayingAudio(null);
      };
    }
  };
  
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
            {['telemetry', 'matrix', 'phonology', 'vision', 'waxal'].map((tab) => (
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
                      <th className="p-10 text-silk-gold">Hausa AI (Prosodic)</th>
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
                We have moved beyond words. Hausa AI calculates the vibration of Standard Hausa through the laws of moraic TBUs and R-to-L melody mapping.
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

          {activeTab === 'waxal' && (
             <div className="space-y-12 animate-reveal">
               {/* Dashboard Stats */}
               {waxalStats ? (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="p-8 rounded-[30px] bg-white/[0.02] border border-white/5">
                      <span className="text-[10px] text-white/40 uppercase tracking-wider block mb-2">Speaker & Demographics</span>
                      <div className="text-3xl font-serif text-silk-gold">{waxalStats.general.total_samples} Total Samples</div>
                      <div className="text-[11px] text-white/50 mt-2">
                        {waxalStats.general.total_speakers} Speakers (4 Male, 4 Female)<br/>
                        Male: {waxalStats.general.male_samples} | Female: {waxalStats.general.female_samples}
                      </div>
                    </div>
                    <div className="p-8 rounded-[30px] bg-white/[0.02] border border-white/5">
                      <span className="text-[10px] text-white/40 uppercase tracking-wider block mb-2">Lexical / Linguistic Metrics</span>
                      <div className="text-3xl font-serif text-silk-gold">{waxalStats.linguistic.vocab_size} Vocab Size</div>
                      <div className="text-[11px] text-white/50 mt-2">
                        Total Words: {waxalStats.linguistic.total_words}<br/>
                        Avg length: {waxalStats.linguistic.avg_sentence_length} words (TTR: {waxalStats.linguistic.type_token_ratio})
                      </div>
                    </div>
                    <div className="p-8 rounded-[30px] bg-white/[0.02] border border-white/5">
                      <span className="text-[10px] text-white/40 uppercase tracking-wider block mb-2">Orthography Hook Contrast</span>
                      <div className="text-3xl font-serif text-silk-gold">
                        {waxalStats.orthography.unicode.d_hook + waxalStats.orthography.unicode.k_hook + waxalStats.orthography.unicode.b_hook + waxalStats.orthography.unicode.y_hook} Hooks
                      </div>
                      <div className="text-[11px] text-white/50 mt-2">
                        Unicode: ɗ:{waxalStats.orthography.unicode.d_hook} | ƙ:{waxalStats.orthography.unicode.k_hook} | ɓ:{waxalStats.orthography.unicode.b_hook} | ƴ:{waxalStats.orthography.unicode.y_hook}<br/>
                        ASCII Hooks (requires Normalization): 'y:{waxalStats.orthography.ascii["'y"] || 0} | k':{waxalStats.orthography.ascii["k'"] || 0} | d':{waxalStats.orthography.ascii["d'"] || 0}
                      </div>
                    </div>
                  </div>
               ) : (
                  <div className="text-center py-6 text-white/40">Loading dataset statistics...</div>
               )}

               {/* Filter & Search Bar */}
               <div className="flex flex-col md:flex-row gap-6 p-6 rounded-[30px] bg-white/5 border border-white/10 items-center justify-between">
                 <div className="flex items-center gap-4 bg-black/40 rounded-full px-6 py-3 border border-white/5 w-full md:w-1/2">
                   <svg className="w-5 h-5 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeWidth="2" strokeLinecap="round"/></svg>
                   <input 
                     type="text" 
                     value={searchQuery}
                     onChange={(e) => { setSearchQuery(e.target.value); setWaxalPage(1); }}
                     placeholder="Bincika rubutu (Search transcript)..." 
                     className="bg-transparent border-none text-white focus:outline-none w-full text-[14px]"
                   />
                 </div>
                 <div className="flex gap-4 w-full md:w-auto">
                   <select 
                     value={speakerFilter} 
                     onChange={(e) => { setSpeakerFilter(e.target.value); setWaxalPage(1); }}
                     className="bg-black/60 border border-white/10 rounded-full px-6 py-3 text-[12px] text-white/70 focus:outline-none"
                   >
                     <option value="">Duk Masu Magana (All Speakers)</option>
                     {Array.from({length: 8}, (_, i) => i + 1).map(num => (
                       <option key={num} value={num.toString()}>Speaker {num}</option>
                     ))}
                   </select>
                   <select 
                     value={genderFilter} 
                     onChange={(e) => { setGenderFilter(e.target.value); setWaxalPage(1); }}
                     className="bg-black/60 border border-white/10 rounded-full px-6 py-3 text-[12px] text-white/70 focus:outline-none"
                   >
                     <option value="">Duk Jinsi (All Genders)</option>
                     <option value="Male">Namiji (Male)</option>
                     <option value="Female">Mace (Female)</option>
                   </select>
                 </div>
               </div>

               {/* Samples Table */}
               <div className="overflow-x-auto rounded-[30px] border border-white/10 bg-white/[0.01]">
                 <table className="w-full text-left">
                   <thead className="bg-white/5 text-[9px] uppercase tracking-wider text-white/40">
                     <tr>
                       <th className="p-6">ID</th>
                       <th className="p-6">Speaker</th>
                       <th className="p-6">Gender</th>
                       <th className="p-6 w-1/2">Transcript (Rubutu)</th>
                       <th className="p-6 text-center">Audio</th>
                     </tr>
                   </thead>
                   <tbody className="text-[13px] text-white/80">
                     {waxalSamples.length > 0 ? (
                       waxalSamples.map(sample => (
                         <tr key={sample.id} className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                           <td className="p-6 font-mono text-[11px] text-white/40">{sample.id}</td>
                           <td className="p-6 font-semibold">Speaker {sample.speaker_id}</td>
                           <td className="p-6 text-white/50">{sample.gender}</td>
                           <td className="p-6 font-serif italic text-white/90 leading-relaxed">{sample.text}</td>
                           <td className="p-6 text-center">
                             <button 
                               onClick={() => playAudio(sample.audio_file)}
                               className={`px-6 py-3 rounded-full text-[10px] font-black uppercase tracking-wider transition-all flex items-center gap-2 mx-auto ${
                                 playingAudio === sample.audio_file 
                                   ? 'bg-red-600 text-white shadow-[0_0_15px_rgba(220,38,38,0.5)] animate-pulse' 
                                   : 'bg-silk-gold text-black hover:scale-105'
                               }`}
                             >
                               {playingAudio === sample.audio_file ? (
                                  <>
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M15.75 5.25v13.5m-7.5-13.5v13.5" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg>
                                    PAUSE
                                  </>
                               ) : (
                                  <>
                                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                                    PLAY
                                  </>
                               )}
                             </button>
                           </td>
                         </tr>
                       ))
                     ) : (
                       <tr>
                         <td colSpan={5} className="p-12 text-center text-white/30 italic">Babu wani samfuri da ya dace da bincikenka.</td>
                       </tr>
                     )}
                   </tbody>
                 </table>
               </div>

               {/* Pagination Controls */}
               {waxalTotalPages > 1 && (
                 <div className="flex items-center justify-between px-4 py-2 border-t border-white/5 pt-6">
                   <button 
                     disabled={waxalPage === 1}
                     onClick={() => setWaxalPage(prev => Math.max(1, prev - 1))}
                     className="px-6 py-3 rounded-full border border-white/10 text-[11px] uppercase tracking-wider text-silk-gold disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/5 transition-all"
                   >
                     Baya (Prev)
                   </button>
                   <span className="text-[12px] font-mono text-white/50">
                     Shafi {waxalPage} na {waxalTotalPages} ({waxalTotalCount} samples)
                   </span>
                   <button 
                     disabled={waxalPage === waxalTotalPages}
                     onClick={() => setWaxalPage(prev => Math.min(waxalTotalPages, prev + 1))}
                     className="px-6 py-3 rounded-full border border-white/10 text-[11px] uppercase tracking-wider text-silk-gold disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/5 transition-all"
                   >
                     Gaba (Next)
                   </button>
                 </div>
               )}
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
