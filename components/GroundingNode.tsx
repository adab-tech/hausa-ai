
import React from 'react';

interface Source {
  title: string;
  uri: string;
  type?: string;
}

export const GroundingNode: React.FC<{ sources: Source[] }> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-12 space-y-4 animate-flourish">
      <div className="flex items-center gap-4 opacity-40">
        <span className="h-[1px] w-8 bg-silk-gold"></span>
        <span className="meta-tag text-[8px] tracking-[0.4em]">Hujojin_Bincike_da_Majiyoyi</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sources.map((source, i) => {
          const isYoutube = source.type === 'youtube' || source.uri.includes('youtube.com') || source.uri.includes('youtu.be');
          const isMaps = source.type === 'taswira' || source.uri.includes('maps.google.com') || source.uri.includes('goo.gl/maps');
          
          return (
            <a 
              key={i} 
              href={source.uri} 
              target="_blank" 
              rel="noopener noreferrer"
              className="group p-4 rounded-2xl border border-white/5 bg-white/5 hover:border-silk-gold/30 hover:bg-silk-gold/5 transition-all duration-500 flex items-center gap-4"
            >
              <div className={`flex-none p-2 rounded-xl ${isYoutube ? 'text-red-500 bg-red-500/10' : isMaps ? 'text-green-500 bg-green-500/10' : 'text-silk-gold bg-silk-gold/10'}`}>
                {isYoutube ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                ) : isMaps ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-bold text-white/80 truncate group-hover:text-silk-gold transition-colors">{source.title}</p>
                <p className="text-[8px] text-white/30 truncate uppercase tracking-widest">{isYoutube ? 'Video' : isMaps ? 'Wuri' : ' Shafin Ilimi'}</p>
              </div>
              <svg className="w-4 h-4 text-white/20 group-hover:text-silk-gold transition-all group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </a>
          );
        })}
      </div>
    </div>
  );
};
