import React, { useState, useEffect, useRef } from 'react';
import { ArewaLogo } from './ArewaLogo.tsx';
import { gemini } from '../services/localService.ts';
import { CorrectionsReview } from './CorrectionsReview.tsx';
import {
  Activity,
  Layers,
  Music,
  Award,
  Search,
  Play,
  Pause,
  Users,
  Sparkles,
  BookOpen,
  ShieldCheck,
  ChevronRight,
  Sliders,
  Database,
  GraduationCap
} from 'lucide-react';

export const NeuralReview: React.FC<{ onClose: () => void; onOpenWhitePaper?: () => void }> = ({ onClose, onOpenWhitePaper }) => {
  const [feedbackStats, setFeedbackStats] = useState<{ up: number; down: number; total: number } | null>(null);
  const [activeTab, setActiveTab] = useState<'telemetry' | 'matrix' | 'phonology' | 'vision' | 'waxal' | 'corrections'>('telemetry');

  useEffect(() => {
    gemini.getFeedbackStats().then(data => {
      if (data) setFeedbackStats(data);
    });
  }, []);

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
    { metric: 'Scholarly Sources', sovereign: '7 (Murya)', others: 'Generic Web Data', advantage: 'Primary Grounding' },
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
      <div className="absolute inset-0 bg-black/85 backdrop-blur-[20px]" onClick={onClose}></div>
      
      <div className="relative w-full max-w-6xl bg-dyn-bg-secondary border border-dyn-border rounded-[40px] shadow-[0_0_80px_var(--glow-color)] overflow-hidden flex flex-col max-h-[92vh] z-10 transition-all duration-700">
        
        {/* Animated grid ambient background */}
        <div className="absolute inset-0 opacity-[0.03] zana-grid pointer-events-none" />
        
        {/* Modal Header */}
        <header className="relative z-10 p-6 sm:p-10 pb-4 sm:pb-6 flex flex-col lg:flex-row items-center justify-between border-b border-dyn-border gap-6 bg-dyn-bg-primary/50 backdrop-blur-md">
          <div className="flex items-center gap-5 text-center sm:text-left">
            <ArewaLogo size={50} className="w-16 h-16 shrink-0" active />
            <div>
              <h2 className="font-serif italic text-3xl sm:text-5xl text-dyn-accent leading-none">Matattarar Bayanai</h2>
              <p className="text-[9px] opacity-50 uppercase tracking-[0.4em] mt-1 text-dyn-text-primary">Sovereign Linguistic Analytics Matrix</p>
            </div>
          </div>
          
          {/* Navigation Tabs */}
          <div className="flex bg-dyn-bg-tertiary/60 p-1 rounded-full w-full lg:w-auto overflow-x-auto no-scrollbar border border-dyn-border">
            {[
              { id: 'telemetry', label: 'Telemetry', icon: Activity },
              { id: 'matrix', label: 'Matrix', icon: Layers },
              { id: 'phonology', label: 'Phonology', icon: Music },
              { id: 'vision', label: 'Core Vibe', icon: Sparkles },
              { id: 'waxal', label: 'WAXAL Corpus', icon: Database },
              { id: 'corrections', label: 'Corrections', icon: GraduationCap }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button 
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap shrink-0 ${
                    activeTab === tab.id 
                      ? 'bg-dyn-accent text-dyn-bg-primary shadow-lg font-bold' 
                      : 'text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </header>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-10 space-y-10 no-scrollbar relative z-10 bg-dyn-bg-secondary/40">
          
          {/* Telemetry Tab */}
          {activeTab === 'telemetry' && (
            <div className="space-y-8 animate-reveal">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                {[
                  { label: 'Scholarly Murya', val: '7', sub: 'Primary Research Sources', desc: ' Newman, Litvinova, and Fada standard papers integrated.' },
                  { label: 'Community Feedback', val: feedbackStats ? feedbackStats.total : '—', sub: 'Total Ratings Recorded', desc: 'Real thumbs up/down submitted by users, stored server-side.' },
                  { label: 'Tone Heuristics', val: 'R→L', sub: 'Tone Mapping Direction', desc: 'Tone melody calculated from Right-to-Left.' },
                  { label: 'Approval Rate', val: feedbackStats && feedbackStats.total > 0 ? Math.round((feedbackStats.up / feedbackStats.total) * 100) + '%' : '—', sub: 'Thumbs Up / Total', desc: 'Share of feedback marked as a good response.' }
                ].map((item, i) => (
                  <div key={i} className="p-6 rounded-3xl bg-dyn-bg-tertiary/30 border border-dyn-border text-center group hover:border-dyn-accent/40 hover:bg-dyn-bg-tertiary/50 transition-all duration-500 shadow-xl">
                    <span className="text-[9px] text-dyn-text-secondary uppercase tracking-widest block mb-3 font-semibold">{item.label}</span>
                    <div className="text-5xl sm:text-6xl font-serif italic text-dyn-accent group-hover:scale-105 transition-transform duration-500">{item.val}</div>
                    <p className="text-[9px] text-dyn-text-muted mt-3 uppercase tracking-wider font-medium">{item.sub}</p>
                    <div className="h-[1px] w-12 bg-dyn-border mx-auto my-3 group-hover:w-20 transition-all"></div>
                    <p className="text-[10px] text-dyn-text-primary/40 italic">{item.desc}</p>
                  </div>
                ))}
              </div>

              {/* Dynamic Stats Chart Area */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border">
                  <h3 className="text-xs uppercase tracking-widest text-dyn-accent mb-4 font-bold flex items-center gap-2">
                    <Sliders className="w-4 h-4" /> Active Processing Pipeline
                  </h3>
                  <p className="text-[10px] text-dyn-text-muted mb-4 italic">Stages run on every response. No accuracy benchmark exists yet — see White Paper for the roadmap.</p>
                  <div className="space-y-3">
                    {[
                      'Hooked Orthography Normalization',
                      'Tonal Heuristic Mapping (R→L)',
                      'Cultural Confidence Scoring',
                    ].map((name, index) => (
                      <div key={index} className="flex items-center justify-between text-[11px] font-mono">
                        <span className="text-dyn-text-secondary">{name}</span>
                        <span className="flex items-center gap-1.5 text-green-400 font-bold uppercase text-[10px]">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-400" /> Active
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border flex flex-col justify-between">
                  <div>
                    <h3 className="text-xs uppercase tracking-widest text-dyn-accent mb-3 font-bold flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4" /> Orthography Normalization
                    </h3>
                    <p className="text-[11px] text-dyn-text-secondary leading-relaxed mb-4">
                      Every chat response is passed through orthography normalization and tonal heuristics before display (see <code>backend/orthography.py</code>) to guard against spelling drift and Enghausa code-mixing.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-white/[0.02] border border-dyn-border rounded-xl text-center">
                      <span className="text-[8px] uppercase tracking-wider text-dyn-text-muted block">Pipeline</span>
                      <span className="text-[10px] text-green-400 font-bold uppercase">Active</span>
                    </div>
                    <div className="p-3 bg-white/[0.02] border border-dyn-border rounded-xl text-center">
                      <span className="text-[8px] uppercase tracking-wider text-dyn-text-muted block">Coverage</span>
                      <span className="text-[10px] text-dyn-accent font-bold uppercase">Every Response</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Phonology Tab */}
          {activeTab === 'phonology' && (
            <div className="space-y-8 animate-reveal">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {primaryAxioms.map((ax, i) => (
                  <div key={i} className="p-6 rounded-3xl border border-dyn-border bg-dyn-bg-tertiary/20 flex flex-col justify-between gap-4 group hover:border-dyn-accent/30 transition-all duration-300">
                    <div className="space-y-2">
                      <span className="text-dyn-accent font-mono text-[9px] uppercase tracking-widest font-bold">Axiom {i + 1}: {ax.rule}</span>
                      <h3 className="text-xl sm:text-2xl font-serif italic text-dyn-text-primary">{ax.desc}</h3>
                    </div>
                    <div className="border-t border-dyn-border pt-4 mt-2 flex items-center gap-3">
                      <Award className="w-4 h-4 text-dyn-accent shrink-0" />
                      <span className="text-[11px] text-dyn-text-secondary"><strong className="text-dyn-text-primary">System Proof:</strong> {ax.proof}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-8 rounded-[40px] bg-dyn-bg-tertiary/10 border border-dyn-border text-center max-w-3xl mx-auto">
                 <p className="text-lg sm:text-xl font-serif italic text-dyn-text-secondary leading-relaxed">
                   "Axiom mapping ensures our deep generative layers respect the tonal logic of Hausa as a Primary African Prosodic System."
                 </p>
              </div>
            </div>
          )}

          {/* Matrix Tab */}
          {activeTab === 'matrix' && (
            <div className="animate-reveal overflow-x-auto rounded-3xl border border-dyn-border bg-dyn-bg-tertiary/10 shadow-xl">
               <div className="min-w-[700px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-dyn-bg-primary/50 text-[10px] uppercase tracking-[0.25em] text-dyn-text-secondary border-b border-dyn-border">
                      <th className="p-6 pl-10 font-bold">Neural Parameter Matrix</th>
                      <th className="p-6 text-dyn-accent font-black">Hausa AI (Murya)</th>
                      <th className="p-6 font-bold">Generic Web LLMs</th>
                      <th className="p-6 pr-10 font-bold">Engineering Edge</th>
                    </tr>
                  </thead>
                  <tbody className="text-base font-medium">
                    {competitiveEdge.map((row, i) => (
                      <tr key={i} className="border-b border-dyn-border/40 hover:bg-white/[0.02] transition-colors duration-300">
                        <td className="p-6 pl-10 font-serif italic text-dyn-text-primary">{row.metric}</td>
                        <td className="p-6 text-dyn-accent font-bold">{row.sovereign}</td>
                        <td className="p-6 text-dyn-text-muted">{row.others}</td>
                        <td className="p-6 pr-10 text-[11px] font-mono text-dyn-text-secondary flex items-center gap-1.5 py-7">
                          <span className="w-1.5 h-1.5 rounded-full bg-dyn-accent" />
                          {row.advantage}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Vision/Vibe Tab */}
          {activeTab === 'vision' && (
            <div className="max-w-3xl mx-auto space-y-12 py-6 text-center animate-reveal">
              <div className="flex justify-center"><ArewaLogo size={90} className="w-24 h-24" active /></div>
              <div className="space-y-4">
                <h3 className="font-serif italic text-5xl sm:text-7xl text-dyn-accent leading-none">Martabar Harshe</h3>
                <p className="text-[10px] text-dyn-text-secondary uppercase tracking-[0.4em] font-black">Advisory Board & Architecture</p>
              </div>
              <p className="text-dyn-text-secondary text-lg sm:text-2xl font-light italic leading-relaxed px-4">
                "Hausa is not a code to be translated word-by-word. It is a vibrating sonic system of high-frequency tonal distinctions. We build digital architectures that capture this dignity."
              </p>
              
              <div className="p-8 rounded-[35px] bg-gradient-to-br from-dyn-accent/10 to-transparent border border-dyn-border flex flex-col sm:flex-row items-center justify-between gap-6 text-left">
                <div className="space-y-1">
                  <p className="text-dyn-accent text-[9px] uppercase tracking-[0.4em] font-black">Lead Engineer / Architect</p>
                  <p className="text-3xl font-serif italic text-dyn-text-primary">Adamu Danjuma Abubakar</p>
                  <p className="text-[10px] text-dyn-text-muted uppercase tracking-widest font-mono">ADAB-TECH RESEARCH LABS, KANO</p>
                </div>
                {onOpenWhitePaper && (
                   <button 
                     onClick={() => { onClose(); onOpenWhitePaper(); }}
                     className="px-8 py-4 rounded-full bg-dyn-accent text-dyn-bg-primary text-[10px] font-black uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-xl shrink-0"
                   >
                     Read White Paper
                   </button>
                )}
              </div>
            </div>
          )}

          {/* WAXAL Corpus Tab */}
          {activeTab === 'waxal' && (
             <div className="space-y-8 animate-reveal">
               
               {/* Dashboard Stats */}
               {waxalStats ? (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Stat Card 1 */}
                    <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border flex flex-col justify-between shadow-lg">
                      <div>
                        <span className="text-[9px] text-dyn-text-secondary uppercase tracking-wider block mb-1 font-bold">Demographics & Voice Counts</span>
                        <div className="text-2xl font-serif text-dyn-accent font-bold">{waxalStats.general.total_samples} Total Samples</div>
                        <div className="text-[10px] text-dyn-text-muted mt-1 uppercase tracking-wider">
                          {waxalStats.general.total_speakers} Speakers (4 Male / 4 Female)
                        </div>
                      </div>
                      
                      {/* Visual Progress Bar for Gender Balance */}
                      <div className="mt-5 space-y-1.5">
                        <div className="flex justify-between text-[9px] font-mono font-bold text-dyn-text-secondary">
                          <span>NAMIJI (MALE): {((waxalStats.general.male_samples/waxalStats.general.total_samples)*100).toFixed(0)}%</span>
                          <span>MACE (FEMALE): {((waxalStats.general.female_samples/waxalStats.general.total_samples)*100).toFixed(0)}%</span>
                        </div>
                        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden flex">
                          <div 
                            className="h-full bg-dyn-accent" 
                            style={{ width: `${(waxalStats.general.male_samples/waxalStats.general.total_samples)*100}%` }}
                          />
                          <div 
                            className="h-full bg-pink-500/70" 
                            style={{ width: `${(waxalStats.general.female_samples/waxalStats.general.total_samples)*100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Stat Card 2 */}
                    <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border flex flex-col justify-between shadow-lg">
                      <div>
                        <span className="text-[9px] text-dyn-text-secondary uppercase tracking-wider block mb-1 font-bold">Lexical Profile</span>
                        <div className="text-2xl font-serif text-dyn-accent font-bold">{waxalStats.linguistic.vocab_size} Vocab Size</div>
                        <div className="text-[10px] text-dyn-text-muted mt-1 uppercase tracking-wider">
                          Total Words: {waxalStats.linguistic.total_words}
                        </div>
                      </div>

                      {/* Visual bar graph representation */}
                      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-dyn-border/30 pt-3 text-[10px] font-mono">
                        <div>
                          <span className="text-dyn-text-muted block text-[8px] uppercase tracking-wider">Avg Sentence</span>
                          <span className="text-dyn-text-primary font-bold text-sm">{waxalStats.linguistic.avg_sentence_length} words</span>
                        </div>
                        <div>
                          <span className="text-dyn-text-muted block text-[8px] uppercase tracking-wider">Token Ratio</span>
                          <span className="text-dyn-text-primary font-bold text-sm">{waxalStats.linguistic.type_token_ratio}</span>
                        </div>
                      </div>
                    </div>

                    {/* Stat Card 3 */}
                    <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border flex flex-col justify-between shadow-lg">
                      <div>
                        <span className="text-[9px] text-dyn-text-secondary uppercase tracking-wider block mb-1 font-bold">Orthography Hook Contrast</span>
                        <div className="text-2xl font-serif text-dyn-accent font-bold">
                          {waxalStats.orthography.unicode.d_hook + waxalStats.orthography.unicode.k_hook + waxalStats.orthography.unicode.b_hook + waxalStats.orthography.unicode.y_hook} Hooks
                        </div>
                        <div className="text-[10px] text-dyn-text-muted mt-1 uppercase tracking-wider">
                          Hooked characters in dataset
                        </div>
                      </div>

                      {/* Hooks visual chips */}
                      <div className="mt-4 flex flex-wrap gap-2">
                        {[
                          { char: 'ɗ', count: waxalStats.orthography.unicode.d_hook },
                          { char: 'ƙ', count: waxalStats.orthography.unicode.k_hook },
                          { char: 'ɓ', count: waxalStats.orthography.unicode.b_hook },
                          { char: 'ƴ', count: waxalStats.orthography.unicode.y_hook }
                        ].map((hk) => (
                          <div key={hk.char} className="px-2.5 py-1 bg-white/5 border border-dyn-border rounded-lg text-center flex items-center gap-1.5">
                            <span className="text-xs font-serif font-black text-dyn-accent">{hk.char}</span>
                            <span className="text-[9px] font-mono text-dyn-text-secondary">{hk.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
               ) : (
                  <div className="text-center py-6 text-dyn-text-secondary/40 font-mono text-xs animate-pulse">Loading corpus dataset analytics...</div>
               )}

               {/* Filter & Search Bar */}
               <div className="flex flex-col md:flex-row gap-4 p-5 rounded-3xl bg-dyn-bg-tertiary/10 border border-dyn-border items-center justify-between">
                 <div className="flex items-center gap-3 bg-black/40 rounded-full px-5 py-2.5 border border-dyn-border w-full md:w-1/2">
                   <Search className="w-4 h-4 text-dyn-text-muted" />
                   <input 
                     type="text" 
                     value={searchQuery}
                     onChange={(e) => { setSearchQuery(e.target.value); setWaxalPage(1); }}
                     placeholder="Bincika rubutu (Search transcript)..." 
                     className="bg-transparent border-none text-dyn-text-primary focus:outline-none w-full text-xs placeholder:text-dyn-text-muted"
                   />
                 </div>
                 <div className="flex flex-wrap gap-3 w-full md:w-auto">
                   <select 
                     value={speakerFilter} 
                     onChange={(e) => { setSpeakerFilter(e.target.value); setWaxalPage(1); }}
                     className="bg-dyn-bg-tertiary border border-dyn-border rounded-full px-5 py-2.5 text-[11px] text-dyn-text-secondary focus:outline-none cursor-pointer"
                   >
                     <option value="">Masu Magana (All Speakers)</option>
                     {Array.from({length: 8}, (_, i) => i + 1).map(num => (
                       <option key={num} value={num.toString()}>Speaker {num}</option>
                     ))}
                   </select>
                   <select 
                     value={genderFilter} 
                     onChange={(e) => { setGenderFilter(e.target.value); setWaxalPage(1); }}
                     className="bg-dyn-bg-tertiary border border-dyn-border rounded-full px-5 py-2.5 text-[11px] text-dyn-text-secondary focus:outline-none cursor-pointer"
                   >
                     <option value="">Jinsi (All Genders)</option>
                     <option value="Male">Namiji (Male)</option>
                     <option value="Female">Mace (Female)</option>
                   </select>
                 </div>
               </div>

               {/* Samples Table */}
               <div className="overflow-x-auto rounded-3xl border border-dyn-border bg-dyn-bg-tertiary/10 shadow-lg">
                 <table className="w-full text-left border-collapse">
                   <thead>
                     <tr className="bg-dyn-bg-primary/50 text-[9px] uppercase tracking-wider text-dyn-text-secondary border-b border-dyn-border">
                       <th className="p-4 pl-6">ID</th>
                       <th className="p-4">Speaker</th>
                       <th className="p-4">Gender</th>
                       <th className="p-4 w-1/2">Transcript (Rubutu)</th>
                       <th className="p-4 text-center">Audio Preview</th>
                     </tr>
                   </thead>
                   <tbody className="text-xs text-dyn-text-primary/90 font-medium">
                     {waxalSamples.length > 0 ? (
                       waxalSamples.map(sample => (
                         <tr key={sample.id} className="border-b border-dyn-border/30 hover:bg-white/[0.01] transition-colors">
                           <td className="p-4 pl-6 font-mono text-[10px] text-dyn-text-muted">{sample.id}</td>
                           <td className="p-4 font-semibold text-dyn-text-primary">Speaker {sample.speaker_id}</td>
                           <td className="p-4 text-dyn-text-muted">{sample.gender}</td>
                           <td className="p-4 font-serif italic text-dyn-text-primary/95 leading-relaxed pr-6">{sample.text}</td>
                           <td className="p-4 text-center">
                             <div className="flex items-center justify-center gap-3">
                               {playingAudio === sample.audio_file && (
                                 <div className="flex gap-0.5 items-center h-4 shrink-0">
                                   <div className="w-0.5 bg-dyn-accent rounded-full animate-bounce h-2" style={{ animationDelay: '0.1s' }}></div>
                                   <div className="w-0.5 bg-dyn-accent rounded-full animate-bounce h-3.5" style={{ animationDelay: '0.3s' }}></div>
                                   <div className="w-0.5 bg-dyn-accent rounded-full animate-bounce h-1.5" style={{ animationDelay: '0.2s' }}></div>
                                   <div className="w-0.5 bg-dyn-accent rounded-full animate-bounce h-3" style={{ animationDelay: '0.4s' }}></div>
                                 </div>
                               )}
                               <button 
                                 onClick={() => playAudio(sample.audio_file)}
                                 className={`px-5 py-2 rounded-full text-[9px] font-black uppercase tracking-wider transition-all flex items-center gap-1.5 ${
                                   playingAudio === sample.audio_file 
                                     ? 'bg-red-600 text-white shadow-[0_0_12px_rgba(220,38,38,0.4)] animate-pulse' 
                                     : 'bg-dyn-accent text-dyn-bg-primary hover:scale-105 active:scale-95'
                                 }`}
                               >
                                 {playingAudio === sample.audio_file ? (
                                    <>
                                      <Pause className="w-3.5 h-3.5" />
                                      <span>TSAYA</span>
                                    </>
                                 ) : (
                                    <>
                                      <Play className="w-3.5 h-3.5 fill-current" />
                                      <span>SAURA</span>
                                    </>
                                 )}
                               </button>
                             </div>
                           </td>
                         </tr>
                       ))
                     ) : (
                       <tr>
                         <td colSpan={5} className="p-10 text-center text-dyn-text-muted italic">Babu wani samfuri da ya dace da bincikenka.</td>
                       </tr>
                     )}
                   </tbody>
                 </table>
               </div>

               {/* Pagination Controls */}
               {waxalTotalPages > 1 && (
                  <div className="flex items-center justify-between px-2 pt-2 border-t border-dyn-border/20">
                    <button 
                      disabled={waxalPage === 1}
                      onClick={() => setWaxalPage(prev => Math.max(1, prev - 1))}
                      className="px-5 py-2.5 rounded-full border border-dyn-border text-[10px] font-bold uppercase tracking-wider text-dyn-accent disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/5 transition-all"
                    >
                      Baya (Prev)
                    </button>
                    <span className="text-[11px] font-mono text-dyn-text-muted">
                      Shafi {waxalPage} na {waxalTotalPages} ({waxalTotalCount} samples)
                    </span>
                    <button 
                      disabled={waxalPage === waxalTotalPages}
                      onClick={() => setWaxalPage(prev => Math.min(waxalTotalPages, prev + 1))}
                      className="px-5 py-2.5 rounded-full border border-dyn-border text-[10px] font-bold uppercase tracking-wider text-dyn-accent disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/5 transition-all"
                    >
                      Gaba (Next)
                    </button>
                  </div>
               )}
             </div>
          )}

          {/* Corrections Review Tab */}
          {activeTab === 'corrections' && <CorrectionsReview />}
        </div>

        {/* Modal Footer */}
        <footer className="p-5 bg-dyn-bg-primary border-t border-dyn-border flex flex-col sm:flex-row justify-between items-center px-10 text-[9px] text-dyn-text-muted uppercase tracking-[0.4em] font-black italic gap-3 relative z-10">
           <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-dyn-accent animate-pulse"></span>
              <span>Grounding Murya: Litvinova Standard</span>
           </div>
           <span>Prosody Rules Sourced From Litvinova &amp; Newman</span>
        </footer>
      </div>
    </div>
  );
};
