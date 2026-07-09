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
        <defs>
          <linearGradient id="formal-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--accent-color)" />
            <stop offset="100%" stopColor="var(--accent-color)" stopOpacity="0.3" />
          </linearGradient>
          <filter id="elegant-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        
        {/* Outer Tech Ring */}
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
        
        {/* Arewa Knot Path: Vertical Figure-8 */}
        <path 
          d="M 50 50 C 65 30 65 10 50 10 C 35 10 35 30 50 50 C 65 70 65 90 50 90 C 35 90 35 70 50 50 Z" 
          stroke="url(#formal-grad)" 
          strokeWidth={active ? "3.2" : "1.8"} 
          strokeLinecap="round" 
          strokeLinejoin="round"
          filter={active ? "url(#elegant-glow)" : "none"}
          className="transition-all duration-700"
          style={{ filter: active ? 'drop-shadow(0 0 8px var(--accent-color))' : 'none' }}
        />

        {/* Arewa Knot Path: Horizontal Figure-8 */}
        <path 
          d="M 50 50 C 70 65 90 65 90 50 C 90 35 70 35 50 50 C 30 65 10 65 10 50 C 10 35 30 35 50 50 Z" 
          stroke="url(#formal-grad)" 
          strokeWidth={active ? "3.2" : "1.8"} 
          strokeLinecap="round" 
          strokeLinejoin="round"
          filter={active ? "url(#elegant-glow)" : "none"}
          className="transition-all duration-700"
          style={{ filter: active ? 'drop-shadow(0 0 8px var(--accent-color))' : 'none' }}
        />

        {/* Central Core Framing Diamond */}
        <path 
          d="M 50 34 L 66 50 L 50 66 L 34 50 Z" 
          stroke="var(--accent-color)" 
          strokeWidth={active ? "1.8" : "1.0"} 
          strokeLinejoin="round"
          className="opacity-70"
        />
        
        {/* Cyber Nodes at the four outer loops */}
        <circle 
          cx="50" 
          cy="10" 
          r={active ? "3.5" : "2"} 
          fill="var(--accent-color)" 
          className={active ? 'animate-pulse' : 'opacity-60'} 
        />
        <circle 
          cx="50" 
          cy="90" 
          r={active ? "3.5" : "2"} 
          fill="var(--accent-color)" 
          className={active ? 'animate-pulse' : 'opacity-60'} 
        />
        <circle 
          cx="10" 
          cy="50" 
          r={active ? "3.5" : "2"} 
          fill="var(--accent-color)" 
          className={active ? 'animate-pulse' : 'opacity-60'} 
        />
        <circle 
          cx="90" 
          cy="50" 
          r={active ? "3.5" : "2"} 
          fill="var(--accent-color)" 
          className={active ? 'animate-pulse' : 'opacity-60'} 
        />

        {/* Center Neural core */}
        <circle cx="50" cy="50" r="5" fill="var(--accent-color)" className={active ? 'animate-pulse' : 'opacity-40'} />
        {active && (
           <circle cx="50" cy="50" r="16" stroke="var(--accent-color)" strokeWidth="0.5" className="animate-ping opacity-15" />
        )}
      </svg>
    </div>
  );
};

