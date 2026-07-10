import React from 'react';

export const ArewaLogo: React.FC<{ size?: number; active?: boolean; watermark?: boolean; className?: string }> = ({ 
  size = 48, 
  active = false, 
  watermark = false,
  className = ""
}) => {
  return (
    <div 
      className={`relative flex items-center justify-center transition-all duration-1000 ${active ? 'scale-110' : 'scale-100'} ${watermark ? 'opacity-[0.02] pointer-events-none fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-0' : 'z-10'} ${className}`} 
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Same mark as the murya.ng landing page: an octagon (8 speakers ·
            Arewa geometry) framing a voice waveform — one brand mark across
            the app and the public site. */}

        {/* Outer Tech Ring (app-only embellishment for the "active" state) */}
        {active && (
          <circle
            cx="50"
            cy="50"
            r="46"
            stroke="var(--accent-color)"
            strokeWidth="0.5"
            strokeDasharray="4 4"
            className="opacity-20 animate-[spin_40s_linear_infinite]"
          />
        )}

        <polygon
          points="90.6,66.9 66.9,90.6 33.1,90.6 9.4,66.9 9.4,33.1 33.1,9.4 66.9,9.4 90.6,33.1"
          stroke="var(--accent-color)"
          strokeWidth={active ? "4.4" : "3.6"}
          strokeLinejoin="round"
          className="transition-all duration-700"
          style={{ filter: active ? 'drop-shadow(0 0 8px var(--accent-color))' : 'none' }}
        />
        <circle cx="37" cy="50" r="4.3" fill="var(--accent-color)" className={active ? 'animate-pulse' : 'opacity-90'} />
        <path d="M44.1,41.6 A11 11 0 0 1 44.1,58.4" stroke="var(--accent-color)" strokeWidth={active ? "4.4" : "3.6"} strokeLinecap="round" className="transition-all duration-700" />
        <path d="M49.2,35.4 A19 19 0 0 1 49.2,64.6" stroke="var(--accent-color)" strokeWidth={active ? "4.4" : "3.6"} strokeLinecap="round" className="transition-all duration-700" />
        <path d="M54.4,29.3 A27 27 0 0 1 54.4,70.7" stroke="var(--accent-color)" strokeWidth={active ? "4.4" : "3.6"} strokeLinecap="round" className="transition-all duration-700" />
        {active && (
           <circle cx="50" cy="50" r="16" stroke="var(--accent-color)" strokeWidth="0.5" className="animate-ping opacity-15" />
        )}
      </svg>
    </div>
  );
};

