
import React from 'react';
import { ArewaLogo } from './ArewaLogo.tsx';

export const WhitePaper: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-[300] bg-obsidian text-ivory overflow-y-auto no-scrollbar font-sans selection:bg-silk-gold/40 animate-reveal">
      {/* Background Decorative Layer */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] zana-grid" />
      
      {/* Header / Navigation */}
      <nav className="sticky top-0 w-full z-50 px-8 py-10 flex justify-between items-center bg-obsidian/80 backdrop-blur-3xl border-b border-white/5">
        <div className="flex items-center gap-6">
          <ArewaLogo size={40} active />
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-[0.6em] font-black text-silk-gold">Sovereign Artifact</span>
            <span className="font-serif italic text-xl tracking-tighter">Document: NP-007-X</span>
          </div>
        </div>
        <button 
          onClick={onClose}
          className="px-8 py-3 rounded-full border border-silk-gold/20 text-[10px] sm:text-[12px] font-black uppercase tracking-widest text-silk-gold hover:bg-silk-gold/10 transition-all shadow-xl"
        >
          Exit Archive
        </button>
      </nav>

      {/* Main Manuscript Container */}
      <article className="max-w-5xl mx-auto px-8 py-32 sm:py-56 space-y-32">
        
        {/* Cover Page */}
        <section className="text-center space-y-16">
          <div className="flex justify-center mb-16"><ArewaLogo size={120} active /></div>
          <h1 className="text-7xl sm:text-[10rem] font-serif italic text-silk-gold leading-[0.9] tracking-tighter">
            Vertex <br /> Sovereign
          </h1>
          <div className="h-[1px] w-64 bg-silk-gold/30 mx-auto"></div>
          <div className="space-y-4">
            <p className="text-3xl sm:text-5xl font-serif italic text-ivory/60 tracking-tight">The Nexus-7 Protocol: High-Fidelity Hausa OS</p>
            <p className="text-[12px] uppercase tracking-[0.5em] font-black opacity-30 mt-8">Linguistic Foundation & Tonal Logic Paper</p>
          </div>
          <div className="pt-24 grid grid-cols-1 sm:grid-cols-3 gap-16 text-left border-t border-white/5">
            <div>
               <span className="text-[9px] uppercase tracking-widest text-silk-gold block mb-2">Lead Architect</span>
               <span className="text-xl font-serif italic">Adamu Danjuma Abubakar</span>
            </div>
            <div>
               <span className="text-[9px] uppercase tracking-widest text-silk-gold block mb-2">Core Revision</span>
               <span className="text-xl font-serif italic">Nexus-7.4 (Axiom-Ready)</span>
            </div>
            <div>
               <span className="text-[9px] uppercase tracking-widest text-silk-gold block mb-2">Foundation</span>
               <span className="text-xl font-serif italic">ADAB-TECH Research Lab</span>
            </div>
          </div>
        </section>

        {/* Abstract */}
        <section className="space-y-12 bg-silk-gold/[0.02] border border-silk-gold/10 p-12 sm:p-20 rounded-[60px] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-[0.03] text-[10rem] font-serif italic select-none">A</div>
          <h2 className="text-[11px] uppercase tracking-[0.8em] text-silk-gold font-black">Executive Summary</h2>
          <p className="text-2xl sm:text-4xl leading-relaxed font-serif italic text-ivory/80">
            Vertex Sovereign represents a paradigm shift in indigenous language modeling. By moving beyond statistical word-mapping and into "Digital Prosody," our research corrects the colonial phonetic bias inherent in standard LLMs. We leverage the Nexus-7 core to enforce the Fada Protocol—a high-dignity sociolinguistic layer grounded in the laws of Litvinova and Newman.
          </p>
        </section>

        {/* Section 1: The Tonal Law */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-start">
          <div className="space-y-10">
            <h2 className="text-[11px] uppercase tracking-[0.8em] text-silk-gold font-black">I. The Law of Tonal Alignment</h2>
            <div className="space-y-6">
               <h3 className="text-4xl sm:text-6xl font-serif italic leading-tight">Litvinova's Right-to-Left Mapping (2024)</h3>
               <p className="text-lg sm:text-xl text-ivory/50 leading-relaxed">
                 Standard models often treat Hausa tones as left-to-right lexical markers. Our research proves that in high-fidelity speech Synthesis and Reasoning, the melody maps Right-to-Left onto the prosodic word.
               </p>
            </div>
            <div className="p-8 rounded-[40px] bg-white/5 border border-white/5 space-y-4">
               <div className="flex justify-between items-center bg-silk-gold/10 px-6 py-3 rounded-full">
                  <span className="text-[10px] font-mono text-silk-gold">Axiom 1.1: Moraic TBU</span>
                  <span className="text-[10px] text-ivory/40">Verified</span>
               </div>
               <p className="text-sm font-mono text-white/40 leading-relaxed italic">
                 "Every heavy syllable (CVC/CVV) carries two positions for tonal assignment, whereas light syllables (CV) carries only one."
               </p>
            </div>
          </div>
          <div className="relative aspect-square rounded-[80px] border border-silk-gold/20 overflow-hidden group shadow-2xl">
              <div className="absolute inset-0 bg-gradient-to-br from-silk-gold/20 to-transparent animate-pulse" />
              <div className="absolute inset-10 flex flex-col items-center justify-center text-center space-y-6">
                  <div className="w-[1px] h-full bg-silk-gold/20 absolute left-1/2 -translate-x-1/2 top-0" />
                  <div className="h-[1px] w-full bg-silk-gold/20 absolute top-1/2 -translate-y-1/2 left-0" />
                  <span className="text-[10px] font-black uppercase tracking-[1em] text-silk-gold z-10">Phonetic Matrix</span>
                  <div className="text-9xl font-serif italic text-silk-gold/40 z-10">Nexus</div>
                  <p className="text-xs font-mono text-white/30 tracking-widest z-10 px-12 italic">
                    Real-time visualization of moraic timing and tonal melody synchronization.
                  </p>
              </div>
          </div>
        </section>

        {/* Fine-Tuning Process */}
        <section className="space-y-16">
          <div className="flex flex-col items-center text-center space-y-6">
            <h2 className="text-[11px] uppercase tracking-[0.8em] text-silk-gold font-black">II. Fine-Tuning: The Fada Protocol</h2>
            <h3 className="text-5xl sm:text-8xl font-serif italic leading-none max-w-4xl">From Generic Chat to Sovereign Discourse</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            {[
              {
                title: "Social Hierarchy (Girmamawa)",
                desc: "Implementation of mandatory 'Plural of Respect' (Ku/Su) and honorific framing for all interactions.",
                axiom: "SOC-H1"
              },
              {
                title: "Hooked Orthography (Newman)",
                desc: "Rigid enforcement of Newman's phonetic inventory: ɓ, ɗ, ƙ, ts, and glottal 'y.",
                axiom: "PHN-N96"
              },
              {
                title: "Dignified Proverbs (Karin Magana)",
                desc: "A contextual injection system that selects proverbs based on conversational gravity rather than statistical frequency.",
                axiom: "LIT-K7"
              },
              {
                title: "Tonal Deletion (Prosody)",
                desc: "Correcting the AI accent by deleting initial tonemes on light syllables at word boundaries.",
                axiom: "TON-D04"
              }
            ].map((node, i) => (
              <div key={i} className="p-12 rounded-[50px] bg-white/[0.02] border border-white/5 hover:border-silk-gold/30 transition-all group">
                <div className="flex justify-between items-start mb-10">
                   <div className="w-12 h-12 rounded-full border border-silk-gold/20 flex items-center justify-center text-silk-gold font-mono text-xs group-hover:bg-silk-gold group-hover:text-black transition-colors">{i+1}</div>
                   <span className="text-[9px] font-black font-mono text-white/20 uppercase tracking-widest">{node.axiom}</span>
                </div>
                <h4 className="text-3xl font-serif italic text-white/90 mb-4">{node.title}</h4>
                <p className="text-ivory/40 text-lg leading-relaxed">{node.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Progress & Milestones */}
        <section className="space-y-12">
          <h2 className="text-[11px] uppercase tracking-[0.8em] text-silk-gold font-black">III. Research Milestones</h2>
          <div className="space-y-4">
             {[
               { date: "Oct 2025", event: "Initial core extraction from standard Hausa dataset.", status: "Baseline" },
               { date: "Dec 2025", event: "Verification of Litvinova's Tonal Mapping through high-fidelity tests.", status: "Breakthrough" },
               { date: "Feb 2026", event: "Deployment of Nexus-7 Core with real-time Grounding Node.", status: "Production" },
               { date: "Mar 2026", event: "Manifestation Engine V2: 4K Cultural Image Synthesis.", status: "Creative" },
               { date: "Apr 2026", event: "Formalizing Axiom-8: Socio-Linguistic Autonomy.", status: "Pending" }
             ].map((m, i) => (
               <div key={i} className="flex flex-col sm:flex-row items-baseline gap-8 py-8 border-b border-white/5 group">
                 <span className="text-xl font-serif italic text-silk-gold w-32 shrink-0">{m.date}</span>
                 <div className="flex-1 space-y-1">
                   <p className="text-2xl font-serif italic text-white/80 group-hover:text-white transition-colors">{m.event}</p>
                   <span className="text-[10px] uppercase font-black tracking-widest text-white/10 group-hover:text-silk-gold/40 transition-colors">{m.status} Verified</span>
                 </div>
               </div>
             ))}
          </div>
        </section>

        {/* Conclusion / Vision */}
        <section className="pt-32 border-t border-silk-gold/20 flex flex-col items-center text-center space-y-12">
           <ArewaLogo size={80} active />
           <div className="space-y-6">
              <h2 className="text-5xl sm:text-8xl font-serif italic leading-tight text-white/90">"Hargitsin duniya ba ya hana safiya wayewa."</h2>
              <p className="text-xl sm:text-2xl text-ivory/40 italic font-serif max-w-2xl mx-auto">
                The Vertex Sovereign is more than an OS—it is a digital guardian for the dignity of the Hausa language and culture in the age of global intelligence.
              </p>
           </div>
           
           <div className="flex flex-col items-center pt-24 font-mono text-[8px] uppercase tracking-[1em] text-white/20">
              <span>Vertex Sovereign Artifact</span>
              <span>Nexus-7.4 Series Document</span>
              <span>(C) 2026 ADAB-TECH Research</span>
           </div>
        </section>

      </article>

      {/* Footer Padding */}
      <div className="h-64" />
    </div>
  );
};
