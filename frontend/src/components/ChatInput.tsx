'use client';

import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react';
import { Send, Loader2, Sparkles, Mic } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Enhanced ChatGPT-style input bar
 */
export default function ChatInput({
  onSend,
  isLoading = false,
  placeholder = 'Tìm kiếm sản phẩm...',
  disabled = false
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, [message]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSend(message.trim());
      setMessage('');
      // Reset height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  };

  return (
    <div className="border-t border-border bg-background/95 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-3xl mx-auto px-4 py-4">
        <form onSubmit={handleSubmit} className="relative">
          <div className={`
            relative flex items-end gap-2 rounded-2xl border bg-card p-2
            shadow-lg transition-all duration-300
            ${isFocused 
              ? 'border-primary/50 shadow-xl shadow-primary/5 ring-2 ring-primary/20' 
              : 'border-border hover:border-muted-foreground/30'
            }
          `}>
            {/* AI Sparkle icon - animated when loading */}
            <div className="flex-shrink-0 p-2">
              <Sparkles className={`w-5 h-5 transition-colors duration-300 ${
                isLoading 
                  ? 'text-primary animate-pulse' 
                  : isFocused 
                    ? 'text-primary' 
                    : 'text-muted-foreground'
              }`} />
            </div>
            
            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder={placeholder}
              disabled={isLoading || disabled}
              rows={1}
              className="
                flex-1 resize-none bg-transparent text-foreground placeholder-muted-foreground
                focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed
                text-base leading-6 py-2 max-h-[200px]
              "
            />
            
            {/* Microphone button (placeholder for future voice input) */}
            <button
              type="button"
              disabled
              className="
                flex-shrink-0 p-2 rounded-lg
                text-muted-foreground/50 cursor-not-allowed
                transition-colors
              "
              title="Voice input (coming soon)"
            >
              <Mic className="w-5 h-5" />
            </button>
            
            {/* Send button */}
            <button
              type="submit"
              disabled={!message.trim() || isLoading || disabled}
              className={`
                flex-shrink-0 p-2.5 rounded-xl
                transition-all duration-200
                ${message.trim() && !isLoading && !disabled
                  ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40 hover:scale-105 active:scale-95'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
                }
              `}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          
          {/* Enhanced hint text */}
          <p className="text-xs text-muted-foreground text-center mt-3 flex items-center justify-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-positive animate-pulse" />
            AI Shopping Assistant đang sẵn sàng hỗ trợ bạn
          </p>
        </form>
      </div>
    </div>
  );
}
