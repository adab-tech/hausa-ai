import React from 'react';
import { SovereignVibe, AddresseeGender } from '../types.ts';
import { ArewaLogo } from './ArewaLogo.tsx';
import {
  Sliders, Volume2, ChevronRight, Activity, BookOpen, Cpu, X, Trash2, UserCircle2,
  Gem, Crown, Zap, GraduationCap, Mic2, Mars, Venus, CircleDashed, CircleCheck, Languages,
} from 'lucide-react';

interface SidebarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  isLoading: boolean;
  isLiveActive: boolean;
  vibe: SovereignVibe;
  setVibe: (v: SovereignVibe) => void;
  showVibeDial: boolean;
  setShowVibeDial: (v: boolean) => void;
  speakerId: number | null;
  setSpeakerId: (id: number | null) => void;
  showSpeakerDial: boolean;
  setShowSpeakerDial: (v: boolean) => void;
  addresseeGender: AddresseeGender;
  setAddresseeGender: (g: AddresseeGender) => void;
  showAddresseeDial: boolean;
  setShowAddresseeDial: (v: boolean) => void;
  learningMode: boolean;
  setLearningMode: (v: boolean) => void;
  onOpenDocumentTool: () => void;
  onOpenContribute: () => void;
  onOpenReview: () => void;
  onOpenWhitePaper: () => void;
  onClearChat: () => void;
  hasMessages: boolean;
}

const ADDRESSEE_LABELS: Record<AddresseeGender, string> = {
  unspecified: 'Ba a bayyana ba (Ask me)',
  masculine: 'Namiji (ka / maka)',
  feminine: 'Mace (ki / miki)',
};

const ADDRESSEE_ICONS: Record<AddresseeGender, React.ElementType> = {
  unspecified: CircleDashed,
  masculine: Mars,
  feminine: Venus,
};

const VIBE_META: Record<SovereignVibe, { icon: React.ElementType; blurb: string }> = {
  Classic: { icon: Gem, blurb: 'Timeless gold & obsidian' },
  Royal: { icon: Crown, blurb: 'Velvet indigo & regalia' },
  Cyberpunk: { icon: Zap, blurb: 'Neon circuits, high voltage' },
  Academic: { icon: GraduationCap, blurb: 'Sepia manuscript, scholarly' },
};

/** The two voices put "in front" for user testing — vetted post-fix
 *  (see the SPEAKER_MAP / WAXAL-match-threshold backend fixes) and given
 *  fictional Hausa names so they read as personas, not raw model slots.
 *  Everything else stays available under "More voices" for QA. */
const FEATURED_VOICES: { id: number; name: string; gender: 'Namiji' | 'Mace' }[] = [
  { id: 0, name: 'Malam Garba', gender: 'Namiji' },
  { id: 4, name: 'Malama Asabe', gender: 'Mace' },
];

function speakerLabel(speakerId: number | null): string {
  if (speakerId === null) return 'Baseline (Auto)';
  const featured = FEATURED_VOICES.find(v => v.id === speakerId);
  if (featured) return `${featured.name} (${featured.gender})`;
  return `Murya ${speakerId < 4 ? `M${speakerId + 1}` : `F${speakerId - 3}`} (${speakerId < 4 ? 'Namiji' : 'Mace'})`;
}

/** Shared row control for dropdown option panels: icon badge, label, and a
 *  clear selected-state checkmark + accent glow (not just a background tint). */
const OptionButton: React.FC<{
  icon: React.ElementType;
  label: string;
  sublabel?: string;
  selected: boolean;
  onClick: () => void;
  role?: 'option';
}> = ({ icon: Icon, label, sublabel, selected, onClick, role }) => (
  <button
    type="button"
    role={role}
    aria-selected={role === 'option' ? selected : undefined}
    onClick={onClick}
    className={`group w-full min-h-[44px] flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-all duration-200 ease-out ${
      selected
        ? 'bg-dyn-accent/15 shadow-[0_0_16px_var(--glow-color)]'
        : 'hover:bg-white/5 active:scale-[0.98]'
    }`}
  >
    <span
      className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-200 ${
        selected
          ? 'bg-dyn-accent/20 text-dyn-accent'
          : 'bg-white/5 text-dyn-text-muted group-hover:text-dyn-text-secondary'
      }`}
    >
      <Icon className="w-4 h-4" />
    </span>
    <span className="flex-1 min-w-0">
      <span className={`block text-[11px] uppercase tracking-wider truncate transition-colors duration-200 ${selected ? 'text-dyn-accent font-bold' : 'text-dyn-text-secondary font-semibold group-hover:text-dyn-text-primary'}`}>
        {label}
      </span>
      {sublabel && (
        <span className="block text-[9px] normal-case tracking-normal text-dyn-text-muted truncate mt-0.5">
          {sublabel}
        </span>
      )}
    </span>
    <CircleCheck
      className={`w-4 h-4 shrink-0 text-dyn-accent transition-all duration-200 ${selected ? 'opacity-100 scale-100' : 'opacity-0 scale-50'}`}
    />
  </button>
);

export const Sidebar: React.FC<SidebarProps> = ({
  sidebarOpen,
  setSidebarOpen,
  isLoading,
  isLiveActive,
  vibe,
  setVibe,
  showVibeDial,
  setShowVibeDial,
  speakerId,
  setSpeakerId,
  showSpeakerDial,
  setShowSpeakerDial,
  addresseeGender,
  setAddresseeGender,
  showAddresseeDial,
  setShowAddresseeDial,
  learningMode,
  setLearningMode,
  onOpenDocumentTool,
  onOpenContribute,
  onOpenReview,
  onOpenWhitePaper,
  onClearChat,
  hasMessages,
}) => {
  const [showMoreVoices, setShowMoreVoices] = React.useState(false);
  return (
    <>
      <aside className={`fixed md:relative top-0 bottom-0 left-0 z-50 w-[290px] bg-dyn-bg-secondary/90 md:bg-dyn-bg-secondary/40 border-r border-dyn-border backdrop-blur-xl md:backdrop-blur-md flex flex-col justify-between p-6 transition-all duration-500 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="space-y-8">

          {/* Brand Logo & Header */}
          <div className="flex items-center gap-4 border-b border-dyn-border/40 pb-5">
            <ArewaLogo size={42} active={isLoading || isLiveActive} />
            <div className="flex flex-col">
              <h1 className="font-serif italic text-3xl text-dyn-accent tracking-tighter leading-none">Murya</h1>
              <span className="text-[9px] text-dyn-text-muted uppercase tracking-[0.25em] font-bold mt-1.5 flex items-center gap-1.5">
                <Cpu className="w-3 h-3 text-dyn-accent shrink-0" /> Sovereign Hausa AI
              </span>
            </div>
            <button onClick={() => setSidebarOpen(false)} aria-label="Rufe menu (Close menu)" className="md:hidden ml-auto p-3 -mr-2 text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Configuration Options */}
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold flex items-center gap-1.5">
                <Sliders className="w-3 h-3 text-dyn-accent" /> Sovereign Vibe / Protocol
              </label>

              <div className="relative">
                <button
                  onClick={() => { setShowVibeDial(!showVibeDial); setShowSpeakerDial(false); setShowAddresseeDial(false); }}
                  aria-haspopup="listbox"
                  aria-expanded={showVibeDial}
                  className={`w-full min-h-[48px] px-4 py-3 bg-dyn-bg-tertiary/60 border rounded-2xl text-xs font-bold uppercase tracking-wider text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-dyn-bg-tertiary transition-all duration-300 ease-out flex items-center justify-between gap-2 ${showVibeDial ? 'border-dyn-accent/50 shadow-[0_0_20px_var(--glow-color)]' : 'border-dyn-border'}`}
                >
                  <span className="flex items-center gap-2.5 min-w-0">
                    {React.createElement(VIBE_META[vibe].icon, { className: 'w-4 h-4 text-dyn-accent shrink-0' })}
                    <span className="truncate">Protocol: {vibe}</span>
                  </span>
                  <ChevronRight className={`w-4 h-4 shrink-0 transform transition-transform duration-300 ease-out ${showVibeDial ? 'rotate-90' : 'rotate-0'}`} />
                </button>
                {showVibeDial && (
                  <div role="listbox" className="absolute top-[52px] left-0 right-0 bg-dyn-bg-tertiary/95 border border-dyn-border rounded-2xl p-2 shadow-2xl z-[100] animate-reveal backdrop-blur-xl origin-top space-y-1">
                    {(['Classic', 'Royal', 'Cyberpunk', 'Academic'] as SovereignVibe[]).map(v => (
                      <OptionButton
                        key={v}
                        role="option"
                        icon={VIBE_META[v].icon}
                        label={v}
                        sublabel={VIBE_META[v].blurb}
                        selected={vibe === v}
                        onClick={() => { setVibe(v); setShowVibeDial(false); }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-dyn-accent" /> Murya / TTS Speaker
              </label>

              <div className="relative">
                <button
                  onClick={() => { setShowSpeakerDial(!showSpeakerDial); setShowVibeDial(false); setShowAddresseeDial(false); }}
                  aria-haspopup="listbox"
                  aria-expanded={showSpeakerDial}
                  className={`w-full min-h-[48px] px-4 py-3 bg-dyn-bg-tertiary/60 border rounded-2xl text-xs font-bold uppercase tracking-wider text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-dyn-bg-tertiary transition-all duration-300 ease-out flex items-center justify-between gap-2 ${showSpeakerDial ? 'border-dyn-accent/50 shadow-[0_0_20px_var(--glow-color)]' : 'border-dyn-border'}`}
                >
                  <span className="flex items-center gap-2.5 min-w-0">
                    {speakerId === null
                      ? <Mic2 className="w-4 h-4 text-dyn-accent shrink-0" />
                      : React.createElement(speakerId < 4 ? Mars : Venus, { className: 'w-4 h-4 text-dyn-accent shrink-0' })}
                    <span className="truncate">{speakerLabel(speakerId)}</span>
                  </span>
                  <ChevronRight className={`w-4 h-4 shrink-0 transform transition-transform duration-300 ease-out ${showSpeakerDial ? 'rotate-90' : 'rotate-0'}`} />
                </button>
                {showSpeakerDial && (
                  <div role="listbox" className="absolute top-[52px] left-0 right-0 bg-dyn-bg-tertiary/98 border border-dyn-border rounded-2xl p-2 shadow-2xl z-[100] animate-reveal backdrop-blur-xl origin-top max-h-[34vh] overflow-y-auto no-scrollbar space-y-1">
                    {FEATURED_VOICES.map(v => (
                      <OptionButton
                        key={v.id}
                        role="option"
                        icon={v.gender === 'Namiji' ? Mars : Venus}
                        label={`${v.name} (${v.gender})`}
                        sublabel="Featured"
                        selected={speakerId === v.id}
                        onClick={() => { setSpeakerId(v.id); setShowSpeakerDial(false); }}
                      />
                    ))}
                    <div className="h-[1px] bg-dyn-border my-1.5"></div>
                    <button
                      type="button"
                      onClick={() => setShowMoreVoices(!showMoreVoices)}
                      className="w-full flex items-center justify-between px-3 py-1.5 text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold hover:text-dyn-text-secondary transition-colors"
                    >
                      <span>More voices</span>
                      <ChevronRight className={`w-3 h-3 transform transition-transform duration-200 ${showMoreVoices ? 'rotate-90' : 'rotate-0'}`} />
                    </button>
                    {showMoreVoices && (
                      <>
                        <OptionButton
                          role="option"
                          icon={Mic2}
                          label="Baseline (Auto)"
                          sublabel="Server default"
                          selected={speakerId === null}
                          onClick={() => { setSpeakerId(null); setShowSpeakerDial(false); }}
                        />
                        {Array.from({length: 8}, (_, i) => i).filter(i => !FEATURED_VOICES.some(v => v.id === i)).map(i => (
                          <OptionButton
                            key={i}
                            role="option"
                            icon={i < 4 ? Mars : Venus}
                            label={`Murya ${i < 4 ? `M${i + 1} (Namiji)` : `F${i - 3} (Mace)`}`}
                            sublabel="WAXAL"
                            selected={speakerId === i}
                            onClick={() => { setSpeakerId(i); setShowSpeakerDial(false); }}
                          />
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold flex items-center gap-1.5">
                <UserCircle2 className="w-3 h-3 text-dyn-accent" /> Yadda za a yi maka/miki magana
              </label>

              <div className="relative">
                <button
                  onClick={() => { setShowAddresseeDial(!showAddresseeDial); setShowVibeDial(false); setShowSpeakerDial(false); }}
                  aria-haspopup="listbox"
                  aria-expanded={showAddresseeDial}
                  className={`w-full min-h-[48px] px-4 py-3 bg-dyn-bg-tertiary/60 border rounded-2xl text-xs font-bold uppercase tracking-wider text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-dyn-bg-tertiary transition-all duration-300 ease-out flex items-center justify-between gap-2 ${showAddresseeDial ? 'border-dyn-accent/50 shadow-[0_0_20px_var(--glow-color)]' : 'border-dyn-border'}`}
                >
                  <span className="flex items-center gap-2.5 min-w-0">
                    {React.createElement(ADDRESSEE_ICONS[addresseeGender], { className: 'w-4 h-4 text-dyn-accent shrink-0' })}
                    <span className="truncate">{ADDRESSEE_LABELS[addresseeGender]}</span>
                  </span>
                  <ChevronRight className={`w-4 h-4 shrink-0 transform transition-transform duration-300 ease-out ${showAddresseeDial ? 'rotate-90' : 'rotate-0'}`} />
                </button>
                {showAddresseeDial && (
                  <div role="listbox" className="absolute top-[52px] left-0 right-0 bg-dyn-bg-tertiary/98 border border-dyn-border rounded-2xl p-2 shadow-2xl z-[100] animate-reveal backdrop-blur-xl origin-top space-y-1">
                    {(Object.keys(ADDRESSEE_LABELS) as AddresseeGender[]).map(g => (
                      <OptionButton
                        key={g}
                        role="option"
                        icon={ADDRESSEE_ICONS[g]}
                        label={ADDRESSEE_LABELS[g]}
                        selected={addresseeGender === g}
                        onClick={() => { setAddresseeGender(g); setShowAddresseeDial(false); }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Learning Mode (Malamin Hausa) toggle */}
            <div className="space-y-2">
              <label className="text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold flex items-center gap-1.5">
                <GraduationCap className="w-3 h-3 text-dyn-accent" /> Yanayin Koyo / Learning
              </label>
              <button
                type="button"
                role="switch"
                aria-checked={learningMode}
                onClick={() => setLearningMode(!learningMode)}
                className={`w-full min-h-[48px] px-4 py-3 border rounded-2xl text-xs font-bold uppercase tracking-wider transition-all duration-300 ease-out flex items-center justify-between gap-2 ${
                  learningMode
                    ? 'bg-dyn-accent/15 border-dyn-accent/50 text-dyn-accent shadow-[0_0_20px_var(--glow-color)]'
                    : 'bg-dyn-bg-tertiary/60 border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-dyn-bg-tertiary'
                }`}
              >
                <span className="flex items-center gap-2.5 min-w-0">
                  <GraduationCap className="w-4 h-4 shrink-0" />
                  <span className="truncate">{learningMode ? 'Malamin Hausa (Kunna)' : 'Yanayin Koyo (Kashe)'}</span>
                </span>
                <span className={`relative w-9 h-5 rounded-full shrink-0 transition-colors ${learningMode ? 'bg-dyn-accent' : 'bg-white/10'}`}>
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${learningMode ? 'left-[18px]' : 'left-0.5'}`}></span>
                </span>
              </button>
              {learningMode && (
                <p className="text-[9px] text-dyn-text-muted/80 italic px-1">Murya na koya maka Hausa da sauran darussa cikin haƙuri. (Tutor mode on.)</p>
              )}
            </div>
          </div>

          {/* Action Links */}
          <div className="space-y-3 pt-6 border-t border-dyn-border/40">
            <button
              onClick={() => { onOpenDocumentTool(); setSidebarOpen(false); }}
              className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 text-dyn-text-primary border border-dyn-border rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all flex items-center gap-3 shadow-sm"
            >
              <Languages className="w-4 h-4 text-dyn-accent" />
              <span>Fassara &amp; Takaitawa</span>
            </button>
            <button
              onClick={() => { onOpenContribute(); setSidebarOpen(false); }}
              className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 text-dyn-text-primary border border-dyn-border rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all flex items-center gap-3 shadow-sm"
            >
              <Mic2 className="w-4 h-4 text-dyn-accent" />
              <span>Gyara Furuci</span>
            </button>
            <button
              onClick={() => { onOpenReview(); setSidebarOpen(false); }}
              className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 text-dyn-text-primary border border-dyn-border rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all flex items-center gap-3 shadow-sm"
            >
              <Activity className="w-4 h-4 text-dyn-accent" />
              <span>Matattarar Bayanai</span>
            </button>
            <button
              onClick={() => { onOpenWhitePaper(); setSidebarOpen(false); }}
              className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 text-dyn-text-primary border border-dyn-border rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all flex items-center gap-3 shadow-sm"
            >
              <BookOpen className="w-4 h-4 text-dyn-accent" />
              <span>White Paper</span>
            </button>
          </div>
        </div>

        {/* System Stats Footer */}
        <div className="space-y-4 border-t border-dyn-border/40 pt-5 text-[10px] font-mono text-dyn-text-muted">
          <div className="flex justify-between">
            <span>Model Tier:</span>
            <span className="text-dyn-accent font-bold">Murya</span>
          </div>
          <div className="flex justify-between">
            <span>Autonomy Level:</span>
            <span className="text-dyn-accent font-bold">FADA Protocol</span>
          </div>
          <button
            onClick={onClearChat}
            disabled={!hasMessages}
            className="w-full min-h-[44px] py-2.5 border border-red-500/20 hover:border-red-500/40 hover:bg-red-500/5 text-red-500/70 hover:text-red-500 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 disabled:opacity-20 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Goge Hira (Clear)</span>
          </button>
        </div>
      </aside>

      {/* Sidebar overlay backdrop for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </>
  );
};
