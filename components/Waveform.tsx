
import React, { useMemo, useEffect, useState } from 'react';

export const Waveform: React.FC<{ active: boolean; volume?: number }> = ({ active, volume = 0 }) => {
  const bars = useMemo(() => Array.from({ length: 40 }), []); // Reduced bar count for mobile performance
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    let animationFrame: number;
    const update = () => {
      setFrame(f => f + 1);
      animationFrame = requestAnimationFrame(update);
    };
    if (active) {
      animationFrame = requestAnimationFrame(update);
    }
    return () => cancelAnimationFrame(animationFrame);
  }, [active]);
  
  return (
    <div className="flex items-center justify-center space-x-[2px] sm:space-x-[4px] h-full w-full overflow-hidden px-4 pointer-events-none">
      {bars.map((_, i) => {
        const dist = Math.abs(i - 20) / 20;
        const baseSize = active ? 10 : 4;
        
        const logVolume = volume > 0 ? Math.log10(1 + volume * 25) : 0;
        // Optimization: Use transform scale instead of height change for smoother GPU frames
        const height = active 
          ? Math.max(baseSize, logVolume * 140 * (1 - Math.pow(dist, 1.3)) * (0.85 + Math.sin(frame / 4 + i / 2) * 0.15)) 
          : baseSize + Math.sin(frame / 20 + i / 4) * 2;
        
        return (
          <div
            key={i}
            className={`w-[3px] sm:w-[5px] rounded-full transition-all duration-75 ease-out ${
              active 
                ? 'bg-silk-gold' 
                : 'bg-white/10'
            }`}
            style={{
              height: `${height}%`,
              opacity: active ? 0.3 + (logVolume * 0.7) : 0.08,
              boxShadow: active && height > 30 ? `0 0 15px rgba(212, 175, 55, 0.3)` : 'none',
              filter: `brightness(${1 + logVolume})`
            }}
          />
        );
      })}
    </div>
  );
};
