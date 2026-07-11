import React, { useRef } from 'react';
import { Attachment } from '../types.ts';
import { Paperclip, Mic, MicOff, SendHorizontal, X } from 'lucide-react';

interface InputConsoleProps {
  inputText: string;
  setInputText: (text: string) => void;
  attachments: Attachment[];
  setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
  isLoading: boolean;
  isLiveActive: boolean;
  onSendMessage: () => void;
  onToggleLiveVoice: () => void;
}

export const InputConsole: React.FC<InputConsoleProps> = ({
  inputText,
  setInputText,
  attachments,
  setAttachments,
  isLoading,
  isLiveActive,
  onSendMessage,
  onToggleLiveVoice,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []) as File[];
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        setAttachments(prev => [...prev, {
          name: file.name,
          mimeType: file.type,
          type: file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio',
          data: event.target?.result as string
        }]);
      };
      reader.readAsDataURL(file);
    });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <footer
      className="p-4 sm:p-6 bg-gradient-to-t from-dyn-bg-primary via-dyn-bg-primary/95 to-transparent relative z-20 border-t border-dyn-border/20"
      style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}
    >
      <div className="max-w-[900px] mx-auto space-y-4">

        {/* Horizontal attachment preview */}
        {attachments.length > 0 && (
          <div className="flex gap-4 overflow-x-auto no-scrollbar py-2 px-1">
             {attachments.map((at, i) => (
               <div key={i} className="flex-none w-20 h-20 rounded-2xl bg-white/5 border border-dyn-border p-1.5 relative shadow-xl transition-transform hover:scale-105">
                  {at.type === 'image' ? (
                    <img src={at.data} alt={at.name || 'Hoton da aka haɗa (attached image)'} className="w-full h-full object-cover rounded-xl" />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-[8px] text-dyn-text-secondary font-mono uppercase bg-black/40 rounded-xl p-1 text-center truncate">
                      <span>{at.name.split('.').pop()}</span>
                      <span className="opacity-50 text-[7px] mt-1">FILE</span>
                    </div>
                  )}
                  <button
                    onClick={() => setAttachments(prev => prev.filter((_, idx) => idx !== i))}
                    aria-label="Cire fayil (Remove attachment)"
                    className="absolute -top-2 -right-2 bg-red-600 text-white rounded-full p-1.5 shadow-2xl hover:scale-110 active:scale-95 transition-transform"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
               </div>
             ))}
          </div>
        )}

        {/* Input Form container */}
        <div className={`flex items-center gap-3 bg-dyn-bg-tertiary/80 backdrop-blur-xl border rounded-[30px] p-2 transition-all duration-300 shadow-2xl ${isLoading ? 'border-dyn-accent/50 shadow-[0_0_20px_rgba(var(--accent-gold-rgb),0.1)]' : 'border-dyn-border hover:border-dyn-accent/40'}`}>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-label="Haɗa fayil (Attach file)"
            className="p-3 sm:p-4 rounded-full text-dyn-text-secondary hover:text-dyn-accent hover:bg-white/5 transition-all shrink-0 active:scale-90"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSendMessage(); } }}
            placeholder="Rubuta saƙonka anan…"
            rows={1}
            aria-label="Shigar da umarni (Message input)"
            className="flex-1 bg-transparent py-2.5 sm:py-3.5 text-base sm:text-lg focus:outline-none placeholder:text-dyn-text-muted/40 font-serif not-italic resize-none no-scrollbar text-dyn-text-primary w-full leading-relaxed"
          />

          <div className="flex items-center gap-2 pr-1 shrink-0">
            <button
              type="button"
              onClick={onToggleLiveVoice}
              aria-label={isLiveActive ? "Kashe murya (Stop live voice)" : "Kunna murya (Start live voice)"}
              className={`p-3 sm:p-4 rounded-full transition-all active:scale-90 ${isLiveActive ? 'bg-red-600 text-white shadow-[0_0_20px_rgba(220,38,38,0.5)] animate-pulse' : 'text-dyn-text-secondary hover:text-dyn-accent hover:bg-white/5'}`}
            >
              {isLiveActive ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
            <button
              type="button"
              onClick={onSendMessage}
              aria-label="Aika saƙo (Send message)"
              disabled={!inputText.trim() && attachments.length === 0}
              className="p-3.5 sm:p-4.5 bg-dyn-accent text-dyn-bg-primary rounded-full shadow-2xl hover:scale-105 active:scale-95 transition-all disabled:opacity-20 disabled:scale-100 disabled:cursor-not-allowed"
            >
              <SendHorizontal className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" multiple />
    </footer>
  );
};
