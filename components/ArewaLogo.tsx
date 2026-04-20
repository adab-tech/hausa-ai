
import React from 'react';

export const ArewaLogo: React.FC<{ size?: number; active?: boolean; watermark?: boolean }> = ({ size = 48, active = false, watermark = false }) => {
  return (
    <div 
      className={`relative flex items-center justify-center transition-all duration-1000 ${active ? 'scale-110' : 'scale-100'} ${watermark ? 'opacity-[0.03] pointer-events-none fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-0' : 'z-10'}`} 
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="formal-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#D4AF37" />
            <stop offset="100%" stopColor="#B8860B" />
          </linearGradient>
          <filter id="elegant-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        
        {/* The Daga Knot - Standard Formal Knot */}
        <path 
          d="M50 4 L75 27 L97 50 L75 73 L50 96 L25 73 L3 50 L25 27 Z" 
          stroke="url(#formal-grad)" 
          strokeWidth={active ? "3.5" : "1.5"} 
          strokeLinecap="round" 
          strokeLinejoin="round"
          filter={active ? "url(#elegant-glow)" : "none"}
          className="transition-all duration-700"
        />
        
        {/* Core Essence */}
        <circle cx="50" cy="50" r="5" fill="#D4AF37" className={active ? 'animate-pulse' : 'opacity-20'} />
        {active && (
           <circle cx="50" cy="50" r="15" stroke="#D4AF37" strokeWidth="0.5" className="animate-ping opacity-10" />
        )}
      </svg>
    </div>
  );
};
