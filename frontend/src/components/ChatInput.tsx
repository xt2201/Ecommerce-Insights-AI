'use client';

import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react';
import { Send, Loader2, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * ChatGPT-style input bar fixed at bottom
 */
export default function ChatInput({
  onSend,
  isLoading = false,
  placeholder = 'Tìm kiếm sản phẩm...',
  disabled = false
}: ChatInputProps) {
  const [message, setMessage] = useState('');
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
    <div className="border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-3xl mx-auto px-4 py-4">
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative flex items-end gap-2 rounded-2xl border border-border bg-card shadow-lg p-2">
            {/* Sparkle icon */}
            <div className="flex-shrink-0 p-2">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            
            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isLoading || disabled}
              rows={1}
              className="
                flex-1 resize-none bg-transparent text-foreground placeholder-muted-foreground
                focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed
                text-base leading-6 py-2 max-h-[200px]
              "
            />
            
            {/* Send button */}
            <button
              type="submit"
              disabled={!message.trim() || isLoading || disabled}
              className="
                flex-shrink-0 p-2.5 rounded-xl
                bg-primary text-primary-foreground
                hover:bg-primary/90 
                disabled:opacity-40 disabled:cursor-not-allowed
                transition-all duration-200
                hover:scale-105 active:scale-95
              "
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          
          {/* Hint text */}
          <p className="text-xs text-muted-foreground text-center mt-2">
            AI Shopping Assistant - Tìm sản phẩm tốt nhất trên Amazon
          </p>
        </form>
      </div>
    </div>
  );
}
